"""
基于 Qwen 2.5 模型的事实一致性校验器
使用真实的 Transformer 模型检测大语言模型的幻觉生成
"""

import torch
import json
import numpy as np
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer,
    LogitsProcessorList,
    LogitsProcessor,
    GenerationConfig
)
import warnings
import time
import os

warnings.filterwarnings("ignore")


@dataclass
class AttentionAnalysis:
    """注意力分析结果"""
    token: str
    token_id: int
    position: int
    system_attention: float    # 对系统提示的注意力总和
    user_attention: float      # 对用户提示的注意力总和
    factuality_score: float    # 事实性得分 (system / (system + user))
    attention_weights: List[float]


@dataclass
class VerificationResult:
    """简化的验证结果"""
    sequence: str
    tokens: List[str]
    factuality_score: float      # 核心指标：事实性得分
    avg_system_attention: float  # 平均系统提示注意力
    avg_user_attention: float    # 平均用户提示注意力
    final_verdict: str           # 最终裁决
    is_hallucination: bool
    analyses: List[Dict[str, Any]]
    verdict_details: Dict[str, Any]


class FactualConsistencyVerifier(LogitsProcessor):
    """
    基于注意力机制的事实一致性校验器
    简化版：检测数字序列开始时对系统提示的最大注意力
    """
    
    def __init__(
        self,
        tokenizer,
        context_length: int,
        system_prompt_length: int,
        model=None,
        max_attention_threshold: float = 0.1,  # 10% 最大注意力阈值
        min_sequence_length: int = 6,
        attention_layer_index: int = -1,  # Use last layer by default
        verbose: bool = True
    ):
        self.tokenizer = tokenizer
        self.context_length = context_length
        self.system_prompt_length = system_prompt_length
        self.model = model
        self.max_attention_threshold = max_attention_threshold
        self.min_sequence_length = min_sequence_length
        self.attention_layer_index = attention_layer_index
        self.verbose = verbose
        
        # 内部状态缓冲
        self.reset_buffers()
        
        # 记录所有分析数据
        self.verification_results = []
        
        # 注意力缓存
        self.attention_cache = {}
        self.generation_step = 0
        
        # 检测状态
        self.number_sequence_started = False
        self.max_system_attention = 0.0
    
    def reset_buffers(self):
        """重置内部缓冲区"""
        self.generated_text = ""  # 累积的生成文本
        self.generated_tokens = []  # 所有生成的token
        self.generation_step = 0
        self.attention_cache = {}
        
        # 序列追踪状态
        self.current_sequence = ""  # 当前正在构建的序列
        self.sequence_start_pos = -1  # 序列开始位置
        self.sequence_tokens = []  # 序列中的tokens
        
        # 检测状态
        self.number_sequence_started = False
        self.max_system_attention = 0.0
    
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        """LogitsProcessor 的主要调用接口"""
        self.generation_step += 1
        
        # 获取最后生成的 token
        if input_ids.shape[1] > self.context_length:
            last_token_id = input_ids[0, -1].item()
            last_token = self.tokenizer.decode([last_token_id])
            current_position = input_ids.shape[1] - 1
            
            # 累积生成的文本
            self.generated_text += last_token
            self.generated_tokens.append((last_token_id, last_token, current_position))
            
            if self.verbose and self.generation_step <= 5:  # 只打印前几个token
                print(f"   🔤 Token {self.generation_step}: '{last_token}'")
            
            # 检测和分析序列
            self._track_sequence(last_token, current_position)
        
        return scores
    
    def _track_sequence(self, token: str, position: int):
        """追踪数字序列并检测注意力"""
        # 忽略前几个token（总是有高峰）
        if position < self.context_length + 5:
            return
            
        # 检查token是否包含数字（数字序列的开始）
        contains_digit = any(char.isdigit() for char in token)
        
        if contains_digit and not self.number_sequence_started:
            # 数字序列开始！
            self.number_sequence_started = True
            if self.verbose:
                print(f"\n🔢 Number sequence started with token: '{token}' at position {position}")
            
        # 继续追踪序列构建
        is_sequence_char = bool(re.match(r'[A-Z0-9\-\s]+$', token.upper()))
        
        if is_sequence_char:
            if self.sequence_start_pos == -1:
                self.sequence_start_pos = len(self.generated_text) - len(token)
                self.current_sequence = token.upper()
                self.sequence_tokens = [(position, token)]
            else:
                self.current_sequence += token.upper()
                self.sequence_tokens.append((position, token))
        else:
            if self.current_sequence and self.sequence_start_pos != -1:
                effective_length = len([c for c in self.current_sequence if c.isalnum()])
                
                if effective_length >= self.min_sequence_length:
                    if self.verbose:
                        print(f"   🔍 Complete sequence detected: {self.current_sequence}")
                    self._record_sequence_result()
                
                self.current_sequence = ""
                self.sequence_start_pos = -1
                self.sequence_tokens = []
    
    def _record_sequence_result(self):
        """记录序列检测结果"""
        sequence = self.current_sequence.strip()
        
        # 构建序列的token信息
        tokens = [token for _, token in self.sequence_tokens]
        
        # 如果检测到数字序列，检查所有生成的token的注意力
        if self.number_sequence_started:
            # 检查所有生成的token位置，不仅仅是序列token
            # 因为最大注意力可能在其他位置
            for position in self.attention_cache.keys():
                if position >= self.context_length:  # 只检查生成的部分
                    self._update_max_system_attention(position)
            
            # 打印注意力矩阵以便调试
            if self.verbose:
                self._print_attention_matrix()
        
        # 基于最大注意力判断是否为幻觉
        if not self.number_sequence_started:
            # 如果没有检测到数字序列开始，无法判断
            verdict = "NO_NUMBER_DETECTED"
            is_hallucination = False
            factuality_score = 0.5
        else:
            # 根据最大注意力判断
            is_hallucination = self.max_system_attention <= self.max_attention_threshold
            if is_hallucination:
                verdict = "HALLUCINATION_DETECTED"
                factuality_score = 0.1
            else:
                verdict = "VERIFIED"
                factuality_score = 0.9
            
            if self.verbose:
                print(f"   📊 Final max attention: {self.max_system_attention:.3f}")
                print(f"   📊 Threshold: {self.max_attention_threshold:.3f}")
                print(f"   📊 Final verdict: {'HALLUCINATION' if is_hallucination else 'NON-HALLUCINATION'}")
        
        result = VerificationResult(
            sequence=sequence,
            tokens=tokens,
            factuality_score=factuality_score,
            avg_system_attention=self.max_system_attention,
            avg_user_attention=0.0,  # 简化版不再计算用户注意力
            final_verdict=verdict,
            is_hallucination=is_hallucination,
            analyses=[],  # 简化版不再需要详细分析
            verdict_details={
                "max_system_attention": self.max_system_attention,
                "threshold": self.max_attention_threshold,
                "number_sequence_started": self.number_sequence_started
            }
        )
        
        self.verification_results.append(result)
        
        if self.verbose:
            print(f"\n📊 Sequence Result: {sequence}")
            print(f"   Verdict: {verdict}")
            print(f"   Max System Attention: {self.max_system_attention:.3f}")
            print(f"   Is Hallucination: {is_hallucination}")
    
    def finalize_sequences(self):
        """在生成结束时分析任何未完成的序列"""
        if self.current_sequence and self.sequence_start_pos != -1:
            # 计算有效长度（去除空格和连字符）
            effective_length = len([c for c in self.current_sequence if c.isalnum()])
            
            if effective_length >= self.min_sequence_length:
                # 序列满足最小长度要求，进行分析
                if self.verbose:
                    print(f"   🔍 Final sequence detected: {self.current_sequence}")
                
                # 记录序列结果
                self._record_sequence_result()
            
            # 重置序列追踪状态
            self.current_sequence = ""
            self.sequence_start_pos = -1
            self.sequence_tokens = []
    
    def _print_attention_heatmap(self, full_matrix):
        """打印注意力热图"""
        print("\n   📊 Attention Heatmap:")
        
        # 创建颜色映射 - 使用不同的字符表示不同的注意力强度
        def get_char_for_value(val):
            if val < 0.01: return '·'    # 0-1%
            elif val < 0.02: return '▁'  # 1-2%
            elif val < 0.05: return '▂'  # 2-5%
            elif val < 0.10: return '▃'  # 5-10%
            elif val < 0.15: return '▄'  # 10-15%
            elif val < 0.20: return '▅'  # 15-20%
            elif val < 0.30: return '▆'  # 20-30%
            elif val < 0.50: return '▇'  # 30-50%
            else: return '█'              # 50%+
        
        # 计算各区域的宽度（防止负数）
        skip_width = 5
        system_width = max(0, self.system_prompt_length - 5)
        user_width = max(0, self.context_length - self.system_prompt_length)
        gen_width = 10  # 减少生成区域的显示宽度
        
        # 限制总宽度
        max_total_width = 80
        if skip_width + system_width + user_width + gen_width > max_total_width:
            # 按比例缩减
            total = skip_width + system_width + user_width + gen_width
            system_width = int(system_width * max_total_width / total)
            user_width = int(user_width * max_total_width / total)
            gen_width = max_total_width - skip_width - system_width - user_width
        
        # 打印边界标记
        print("\n      " + "─" * skip_width + "┬" + "─" * system_width + "┬" + 
              "─" * user_width + "┬" + "─" * gen_width)
        
        # 打印区域标签
        skip_label = "SKIP"
        system_label = "SYSTEM" if system_width >= 6 else "SYS"
        user_label = "USER" if user_width >= 4 else "U"
        gen_label = "GEN"
        
        # 计算标签位置
        skip_padding = max(0, (skip_width - len(skip_label)) // 2)
        system_padding = max(0, (system_width - len(system_label)) // 2)
        user_padding = max(0, (user_width - len(user_label)) // 2)
        gen_padding = max(0, (gen_width - len(gen_label)) // 2)
        
        # 构建标签行
        label_line = "      "
        label_line += " " * skip_padding + skip_label[:skip_width]
        label_line += " " * max(0, skip_width - skip_padding - len(skip_label)) + "│"
        
        if system_width > 0:
            label_line += " " * system_padding + system_label[:system_width]
            label_line += " " * max(0, system_width - system_padding - len(system_label))
        label_line += "│"
        
        if user_width > 0:
            label_line += " " * user_padding + user_label[:user_width]
            label_line += " " * max(0, user_width - user_padding - len(user_label))
        label_line += "│"
        
        label_line += " " * gen_padding + gen_label
        print(label_line)
        
        print("      " + "─" * skip_width + "┴" + "─" * system_width + "┴" + 
              "─" * user_width + "┴" + "─" * gen_width)
        
        # 打印每一行
        for i, row in enumerate(full_matrix[:min(20, len(full_matrix))]):  # 最多显示20行
            # 打印行号
            print(f"   {i:2d} ", end="")
            
            # 打印注意力值 - 限制宽度以避免换行
            max_display_width = min(80, self.context_length + 10)  # 最多显示80个字符
            for j, val in enumerate(row[:min(max_display_width, len(row))]):
                # 在边界处添加分隔符
                if j == 5:
                    print("│", end="")
                elif j == self.system_prompt_length:
                    print("│", end="")
                elif j == self.context_length:
                    print("│", end="")
                    
                # 打印注意力字符
                print(get_char_for_value(val), end="")
            
            # 在行末显示该行的最大值位置和值
            if row:
                max_val = max(row)
                max_idx = row.index(max_val)
                print(f"  ← max: {max_val*100:.1f}% at pos {max_idx}", end="")
            
            print()  # 换行
        
        if len(full_matrix) > 20:
            print(f"      ... ({len(full_matrix) - 20} more rows)")
        
        # 打印图例
        print("\n      Legend: · <1%  ▁ 1-2%  ▂ 2-5%  ▃ 5-10%  ▄ 10-15%  ▅ 15-20%  ▆ 20-30%  ▇ 30-50%  █ >50%")
        print("      Regions: │<-SKIP->│<-----SYSTEM----->│<--USER-->│<-GEN->")
        
        # 打印系统提示区域的最大注意力
        if full_matrix:
            max_system_attention = 0.0
            max_system_pos = -1
            for row in full_matrix:
                for j in range(5, min(self.system_prompt_length, len(row))):
                    if row[j] > max_system_attention:
                        max_system_attention = row[j]
                        max_system_pos = j
            
            print(f"\n      📍 Max attention in SYSTEM region: {max_system_attention*100:.2f}% at position {max_system_pos}")
            print(f"      🎯 Threshold: 10.00% - Verdict: {'✓ NON-HALLUCINATION' if max_system_attention > 0.1 else '✗ HALLUCINATION'}")
    
    def _print_attention_matrix(self):
        """打印注意力矩阵用于调试"""
        print("\n   🎯 Attention Matrix Visualization:")
        print(f"      Context boundary: {self.context_length}")
        print(f"      System prompt boundary: {self.system_prompt_length}")
        
        # 获取完整注意力矩阵
        full_matrix = self.get_full_attention_matrix()
        if not full_matrix:
            print("      No attention matrix available")
            return
            
        print(f"      Matrix shape: {len(full_matrix)} generated tokens")
        
        # 首先打印完整的注意力热图
        self._print_attention_heatmap(full_matrix)
        
        # 打印前几行的注意力分布
        for i in range(min(10, len(full_matrix))):
            row = full_matrix[i]
            print(f"\n      Generated token {i} attention distribution:")
            
            # 找出这一行中的最高注意力值
            if row:
                max_val = max(row)
                max_idx = row.index(max_val)
                
                # 打印前5个最高的注意力值
                sorted_indices = sorted(range(len(row)), key=lambda k: row[k], reverse=True)[:5]
                print(f"        Top 5 positions:")
                for idx in sorted_indices:
                    val = row[idx]
                    if idx < self.system_prompt_length:
                        region = "SYSTEM" if idx >= 5 else "SKIP"
                    elif idx < self.context_length:
                        region = "USER"
                    else:
                        region = "GEN"
                    print(f"          Pos {idx:3d} ({region:6s}): {val*100:6.2f}%")
                
                # 计算各区域的注意力总和
                skip_attn = sum(row[j] for j in range(min(5, len(row))))
                system_attn = sum(row[j] for j in range(5, min(self.system_prompt_length, len(row))))
                user_attn = sum(row[j] for j in range(self.system_prompt_length, min(self.context_length, len(row))))
                gen_attn = sum(row[j] for j in range(self.context_length, len(row)))
                
                print(f"        Region totals: SKIP={skip_attn*100:.1f}%, SYSTEM={system_attn*100:.1f}%, USER={user_attn*100:.1f}%, GEN={gen_attn*100:.1f}%")
    
    def _update_max_system_attention(self, position: int):
        """更新系统提示部分的最大注意力"""
        if position not in self.attention_cache:
            return
            
        attention = self.attention_cache[position]
        if isinstance(attention, torch.Tensor):
            attention_np = attention.cpu().numpy()
        else:
            attention_np = np.array(attention)
            
        # Check attention to ALL tokens in the prompt (not just system prompt)
        # This will help us debug where the high attention is
        prompt_attention = attention_np[:self.context_length]
        
        # Find max attention in entire prompt
        max_prompt_attention = float(np.max(prompt_attention))
        max_prompt_idx = np.argmax(prompt_attention)
        
        # Check system prompt but skip first 5 tokens (they always have high attention)
        start_idx = 5  # Skip first 5 tokens
        end_idx = self.system_prompt_length
        
        # Debug: Always show attention distribution for number sequences
        if self.number_sequence_started and self.verbose:
            print(f"\n   📊 Attention Debug at position {position}:")
            print(f"      Attention check range: {start_idx} to {end_idx} (system prompt except first 5)")
            print(f"      Context length: {self.context_length}")
            print(f"      Total attention length: {len(attention_np)}")
            
            # Show top 10 attention positions in the entire prompt
            top_10_indices = np.argsort(prompt_attention)[-10:][::-1]
            print(f"      Top 10 attention positions in prompt:")
            for idx in top_10_indices:
                print(f"        Position {idx}: {prompt_attention[idx]:.4f} ({prompt_attention[idx]*100:.2f}%)")
        
        if start_idx < end_idx and end_idx <= len(attention_np):
            prompt_attention_slice = attention_np[start_idx:end_idx]
            current_max = float(np.max(prompt_attention_slice)) if len(prompt_attention_slice) > 0 else 0.0
            
            # Debug: print the actual slice being used
            if self.verbose and self.number_sequence_started:
                print(f"      Slicing attention[{start_idx}:{end_idx}], length={len(prompt_attention_slice)}")
                if len(prompt_attention_slice) > 0:
                    print(f"      Raw max value in slice: {current_max}")
                    # Show the actual values in the prompt attention slice
                    top_5_in_slice = np.argsort(prompt_attention_slice)[-5:][::-1]
                    print(f"      Top 5 positions in prompt slice:")
                    for i in top_5_in_slice:
                        actual_pos = start_idx + i
                        print(f"        Relative pos {i} (absolute {actual_pos}): {prompt_attention_slice[i]:.4f}")
            
            # Debug: print if there's a discrepancy
            if max_prompt_attention > current_max * 1.5:  # Significant difference
                if self.verbose:
                    print(f"   🔍 High attention found outside system prompt range!")
                    print(f"      Max in entire prompt: {max_prompt_attention:.3f} at position {max_prompt_idx}")
                    print(f"      Max in system prompt (5-{end_idx}): {current_max:.3f}")
                    # Let's see what tokens have high attention
                    top_indices = np.argsort(prompt_attention)[-5:][::-1]
                    top_values = [f"{prompt_attention[i]:.4f}" for i in top_indices]
                    print(f"      Top 5 attention positions: {top_indices} with values: {top_values}")
            
            # Update global max with system prompt attention
            if current_max > self.max_system_attention:
                self.max_system_attention = current_max
                if self.verbose:
                    print(f"   📊 New max attention found: {self.max_system_attention:.3f} at position {position}")
    

    

    
    def update_attention_cache(self, position: int, attention_weights):
        """更新注意力缓存"""
        self.attention_cache[position] = attention_weights
    
    def get_full_attention_matrix(self):
        """获取完整的注意力矩阵 - 包含所有生成token的注意力权重"""
        if not self.attention_cache:
            return []
        
        # 找出所有位置的最大长度
        max_position = max(self.attention_cache.keys())
        min_position = min(self.attention_cache.keys())
        
        # 确定生成部分的起始位置（context_length之后的第一个位置）
        start_position = max(self.context_length, min_position)
        
        # 构建完整矩阵 - 包含所有生成的token
        full_matrix = []
        missing_positions = []
        
        # 为了形成正确的三角形模式，需要确保每行的长度递增
        for pos in range(start_position, max_position + 1):
            if pos in self.attention_cache:
                weights = self.attention_cache[pos]
                if isinstance(weights, torch.Tensor):
                    weights = weights.cpu().numpy().tolist()
                elif isinstance(weights, np.ndarray):
                    weights = weights.tolist()
                
                # 确保权重长度正确（应该是 pos + 1）
                if len(weights) < pos + 1:
                    # 如果权重太短，在末尾补零
                    weights = weights + [0.0] * (pos + 1 - len(weights))
                elif len(weights) > pos + 1:
                    # 如果权重太长，截断
                    weights = weights[:pos + 1]
                
                full_matrix.append(weights)
            else:
                # 记录缺失的位置，用零填充
                missing_positions.append(pos)
                # 获取预期的权重长度
                expected_length = pos + 1  # 注意力应该覆盖到当前位置
                full_matrix.append([0.0] * expected_length)
        
        if missing_positions and self.verbose:
            print(f"   ⚠️  Warning: Missing attention data for positions: {missing_positions}")
        
        if self.verbose:
            print(f"   ✅ Full attention matrix: {len(full_matrix)} tokens from position {start_position} to {max_position}")
            print(f"   ✅ Total positions in cache: {len(self.attention_cache)}")
            print(f"   ✅ System prompt boundary: {self.system_prompt_length}")
            print(f"   ✅ User prompt boundary: {self.context_length}")
            # 打印矩阵形状以验证三角形模式
            if full_matrix:
                print(f"   ✅ Matrix shape - First row length: {len(full_matrix[0])}, Last row length: {len(full_matrix[-1])}")
                # 验证是否为三角形模式
                is_triangular = all(len(full_matrix[i]) == start_position + i + 1 for i in range(len(full_matrix)))
                print(f"   ✅ Triangular pattern: {'YES' if is_triangular else 'NO'}")
        
        return full_matrix


def capture_attention_hook(verifier, layer_idx, verbose=False):
    """创建一个钩子函数来捕获注意力权重"""
    def hook(module, input, output):
        try:
            # 处理不同的输出格式
            attention_weights = None
            
            # 尝试多种方式获取注意力权重
            if hasattr(output, 'attentions') and output.attentions is not None:
                attention_weights = output.attentions
            elif isinstance(output, tuple) and len(output) > 1:
                # 有些模型将注意力作为元组的第二个元素返回
                for item in output:
                    if isinstance(item, torch.Tensor) and len(item.shape) == 4:
                        # 检查是否为注意力权重的形状 [batch, heads, seq, seq]
                        attention_weights = item
                        break
            elif isinstance(output, dict) and 'attentions' in output:
                attention_weights = output['attentions']
            
            if attention_weights is not None:
                if isinstance(attention_weights, (list, tuple)):
                    # 根据配置选择特定层
                    layer_index = verifier.attention_layer_index
                    if layer_index >= 0 and layer_index < len(attention_weights):
                        attention_weights = attention_weights[layer_index]
                    elif layer_index < 0 and abs(layer_index) <= len(attention_weights):
                        # 支持负索引，-1 为最后一层
                        attention_weights = attention_weights[layer_index]
                    else:
                        # 如果索引越界，使用最后一层
                        if verbose:
                            print(f"   [DEBUG] Layer index {layer_index} out of range, using last layer")
                        attention_weights = attention_weights[-1]
                
                if isinstance(attention_weights, torch.Tensor) and attention_weights.dim() >= 3:
                    # 获取最后一个token的注意力分布
                    # 形状通常是 [batch, num_heads, seq_len, seq_len]
                    if attention_weights.dim() == 4:
                        # 平均所有注意力头
                        avg_attention = attention_weights[0, :, -1, :].mean(dim=0)
                    else:
                        # 可能已经是平均后的注意力
                        avg_attention = attention_weights[0, -1, :]
                    
                    current_pos = avg_attention.shape[0] - 1
                    verifier.update_attention_cache(current_pos, avg_attention)
                    
                    if verbose:
                        print(f"   [DEBUG] Captured attention at position {current_pos}, shape: {avg_attention.shape}")
                        print(f"   [DEBUG] Attention sum: {avg_attention.sum().item():.4f}")
                        # 显示注意力分布的前几个和后几个值
                        if current_pos > verifier.context_length:
                            context_attn = avg_attention[:verifier.context_length].sum().item()
                            generated_attn = avg_attention[verifier.context_length:].sum().item()
                            print(f"   [DEBUG] Context attention: {context_attn:.4f}, Generated attention: {generated_attn:.4f}")
        except Exception as e:
            if verbose:
                print(f"   [DEBUG] Error in attention hook: {e}")
    
    return hook


def load_test_cases(file_path: str = "test_cases.json") -> List[Dict[str, Any]]:
    """从JSON文件加载测试用例"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"测试用例文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['test_cases']


def run_verification(
    model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
    test_cases_file: str = "test_cases.json",
    attention_layer_index: int = -1
):
    """运行验证测试"""
    print("🚀 初始化 Qwen 2.5 模型和分词器...")
    print(f"   模型: {model_name}")
    
    # 加载模型和分词器
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # 设置 pad_token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 检测可用设备
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"   使用设备: {device}")
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float32 if device == "cpu" else torch.float16,
        trust_remote_code=True,
        attn_implementation="eager"  # 使用 eager attention 以支持 output_attentions
    )
    
    # 移动模型到设备
    model = model.to(device)
    
    # 获取模型层数
    num_layers = None
    # 尝试从模型配置中获取层数
    if hasattr(model, 'config'):
        if hasattr(model.config, 'num_hidden_layers'):
            num_layers = model.config.num_hidden_layers
        elif hasattr(model.config, 'n_layer'):
            num_layers = model.config.n_layer
        elif hasattr(model.config, 'num_layers'):
            num_layers = model.config.num_layers
    
    # 如果从配置中无法获取，尝试计算transformer层数
    if num_layers is None:
        transformer_layers = 0
        for name, _ in model.named_modules():
            if any(pattern in name.lower() for pattern in ['layer.', 'layers.', 'h.', 'transformer.h.']):
                # 计算包含数字的层模块
                parts = name.split('.')
                for part in parts:
                    if part.isdigit():
                        layer_idx = int(part)
                        transformer_layers = max(transformer_layers, layer_idx + 1)
        if transformer_layers > 0:
            num_layers = transformer_layers
    
    print("✅ 模型加载完成")
    if num_layers:
        print(f"   模型层数: {num_layers} 层 (有效索引: 0 到 {num_layers-1}, 或 -1 到 -{num_layers})")
        
        # 确定实际使用的层
        if attention_layer_index >= 0:
            if attention_layer_index < num_layers:
                actual_layer = attention_layer_index
                print(f"   注意力层: 使用第 {actual_layer} 层 (索引: {attention_layer_index})")
            else:
                actual_layer = num_layers - 1
                print(f"   ⚠️  警告: 指定的层索引 {attention_layer_index} 超出范围，将使用最后一层 (第 {actual_layer} 层)")
        else:
            if abs(attention_layer_index) <= num_layers:
                actual_layer = num_layers + attention_layer_index
                print(f"   注意力层: 使用第 {actual_layer} 层 (索引: {attention_layer_index})")
            else:
                actual_layer = 0
                print(f"   ⚠️  警告: 指定的层索引 {attention_layer_index} 超出范围，将使用第一层 (第 0 层)")
    else:
        print(f"   注意力层索引: {attention_layer_index}")
    
    # 加载测试用例
    print(f"\n📋 加载测试用例: {test_cases_file}")
    test_cases = load_test_cases(test_cases_file)
    print(f"   找到 {len(test_cases)} 个测试用例")
    
    all_results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*80}")
        print(f"📝 测试用例 {i+1}/{len(test_cases)}: {test_case['name']}")
        print(f"   类别: {test_case['category']}")
        print(f"   描述: {test_case['description']}")
        
        # 构建输入
        messages = [
            {"role": "system", "content": test_case['system_prompt']},
            {"role": "user", "content": test_case['user_prompt']}
        ]
        
        # 计算系统提示的长度 - 需要更准确的方法
        # 编码完整消息，然后找到系统提示的结束位置
        # 先编码只有系统消息的版本
        system_only_text = tokenizer.apply_chat_template(
            [{"role": "system", "content": test_case['system_prompt']}],
            tokenize=False,
            add_generation_prompt=True  # 添加生成提示以匹配完整版本
        )
        
        # 编码系统+用户消息，找到用户消息开始的位置
        full_messages_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize both to find the boundary
        system_only_ids = tokenizer(system_only_text, return_tensors="pt")['input_ids'][0]
        full_ids = tokenizer(full_messages_text, return_tensors="pt")['input_ids'][0]
        
        # 调试输出
        print(f"\n   🔍 Token 边界调试:")
        print(f"      System-only length: {len(system_only_ids)}")
        print(f"      Full message length: {len(full_ids)}")
        
        # 解码前20个token查看
        print(f"      First 20 tokens of full message:")
        for i in range(min(20, len(full_ids))):
            token = tokenizer.decode([full_ids[i].item()])
            print(f"        {i}: '{token}'")
        
        # 更保守的方法：使用用户消息的标记来找边界
        user_message_marker = "user"  # 或其他标记
        
        # 找到包含 "user" 角色标记的位置
        system_prompt_length = len(system_only_ids) - 2  # 减去生成提示部分
        
        # 查找用户消息开始的位置
        # 方法1: 查找 "<|im_start|>user" 的模式
        user_start_found = False
        for i in range(10, len(full_ids) - 10):
            # 解码一段较长的序列来找到完整的模式
            decoded_segment = tokenizer.decode(full_ids[i:i+10].tolist())
            if "<|im_start|>user" in decoded_segment:
                # 找到了user标记的开始，但需要找到内容开始的位置
                # 通常在 "<|im_start|>user\n" 之后
                for j in range(i, min(i+10, len(full_ids))):
                    token = tokenizer.decode([full_ids[j].item()])
                    if token == '\n' and j > i:  # 找到user后的换行符
                        system_prompt_length = j + 1  # 内容在换行符之后开始
                        user_start_found = True
                        print(f"      Found user content start at position {system_prompt_length}")
                        break
                if user_start_found:
                    break
        
        # 如果没找到，使用备用方法
        if not user_start_found:
            # 解码一些关键位置的tokens来调试
            print(f"      Checking tokens around estimated boundary:")
            check_start = max(0, len(system_only_ids) - 10)
            check_end = min(len(full_ids), len(system_only_ids) + 20)
            for i in range(check_start, check_end):
                if i < len(full_ids):
                    token = tokenizer.decode([full_ids[i].item()])
                    print(f"        {i}: '{token}'")
            
            # 使用保守估计
            system_prompt_length = len(system_only_ids)
        
        # 编码完整的输入
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = tokenizer(text, return_tensors="pt")
        # 将输入移到模型所在的设备
        inputs = {k: v.to(device) for k, v in inputs.items()}
        context_length = inputs['input_ids'].shape[1]
        
        print(f"\n   📏 Token边界信息:")
        print(f"      系统提示长度: {system_prompt_length} tokens")
        print(f"      总上下文长度: {context_length} tokens")
        print(f"      用户提示长度: {context_length - system_prompt_length} tokens")
        
        # 显示系统提示部分的最后几个token，帮助验证边界
        if system_prompt_length > 5:
            print(f"      System prompt last 5 tokens (positions {system_prompt_length-5} to {system_prompt_length-1}):")
            for i in range(max(0, system_prompt_length-5), system_prompt_length):
                if i < len(full_ids):
                    token = tokenizer.decode([full_ids[i].item()])
                    print(f"        {i}: '{token}'")
        
        # 创建校验器
        verifier = FactualConsistencyVerifier(
            tokenizer=tokenizer,
            context_length=context_length,
            system_prompt_length=system_prompt_length,
            model=model,
            max_attention_threshold=0.1,  # 10% threshold (adjusted based on empirical data)
            attention_layer_index=attention_layer_index,
            verbose=True
        )
        
        # 设置生成配置
        generation_config = GenerationConfig(
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1
        )
        
        # 生成并验证
        print("\n🔍 开始生成并验证...")
        start_time = time.time()
        
        with torch.no_grad():
            # 注册钩子来捕获注意力
            hooks = []
            hook_count = 0
            for name, module in model.named_modules():
                # 尝试多种模块名称模式
                if any(pattern in name.lower() for pattern in ['attn', 'attention', 'self_attn']):
                    if hasattr(module, 'forward'):
                        hook = module.register_forward_hook(capture_attention_hook(verifier, hook_count, verbose=False))
                        hooks.append(hook)
                        hook_count += 1
            
            try:
                outputs = model.generate(
                    **inputs,
                    generation_config=generation_config,
                    logits_processor=LogitsProcessorList([verifier]),
                    output_attentions=True,
                    output_scores=True,
                    return_dict_in_generate=True
                )
            finally:
                # 移除钩子
                for hook in hooks:
                    hook.remove()
                
                # 分析任何未完成的序列
                verifier.finalize_sequences()
        
        generation_time = time.time() - start_time
        
        # 尝试从输出中提取注意力权重
        if hasattr(outputs, 'attentions') and outputs.attentions is not None:
            if verifier.verbose:
                print(f"   [DEBUG] Found attentions in generate output")
            # 处理生成过程中的注意力权重
            try:
                for step_idx, step_attentions in enumerate(outputs.attentions):
                    if step_attentions is not None and len(step_attentions) > 0:
                        # 根据配置选择特定层的注意力
                        layer_index = verifier.attention_layer_index
                        total_layers = len(step_attentions)
                        
                        if layer_index >= 0 and layer_index < total_layers:
                            selected_layer_attention = step_attentions[layer_index]
                            actual_layer = layer_index
                        elif layer_index < 0 and abs(layer_index) <= total_layers:
                            selected_layer_attention = step_attentions[layer_index]
                            actual_layer = total_layers + layer_index
                        else:
                            # 如果索引越界，使用最后一层
                            if verifier.verbose:
                                print(f"   [DEBUG] Layer index {layer_index} out of range for {total_layers} layers, using last layer")
                            selected_layer_attention = step_attentions[-1]
                            actual_layer = total_layers - 1
                        
                        # 在第一个step时显示层信息
                        if step_idx == 0 and verifier.verbose:
                            print(f"   [DEBUG] Total model layers: {total_layers}, using layer {actual_layer} (index: {layer_index})")
                        
                        last_layer_attention = selected_layer_attention
                        if isinstance(last_layer_attention, torch.Tensor):
                            # 平均所有头
                            # last_layer_attention shape: [batch, heads, seq_len, seq_len]
                            # 注意：每个step的attention矩阵大小是递增的
                            # step 0: shape [1, heads, context_length+1, context_length+1]
                            # step 1: shape [1, heads, context_length+2, context_length+2]
                            # 等等...
                            
                            # 获取当前序列的最后一个位置（即刚生成的token）
                            current_seq_len = last_layer_attention.shape[2]
                            last_pos = current_seq_len - 1
                            
                            # 获取最后一个token对所有之前token的注意力
                            avg_attention = last_layer_attention[0, :, last_pos, :].mean(dim=0)
                            
                            # 实际的序列位置
                            seq_pos = context_length + step_idx
                            verifier.update_attention_cache(seq_pos, avg_attention)
                            
                            if verifier.verbose and step_idx < 3:  # 只打印前几个
                                print(f"   [DEBUG] Step {step_idx}: attention shape {last_layer_attention.shape}, extracted shape {avg_attention.shape}, position {seq_pos}")
            except Exception as e:
                if verifier.verbose:
                    print(f"   [DEBUG] Error processing generate attentions: {e}")
        else:
            print(f"   ⚠️  WARNING: No attention weights in model output. Model may not support attention output.")
            print(f"   [DEBUG] Output attributes: {list(outputs.keys()) if hasattr(outputs, 'keys') else dir(outputs)[:5]}")
        
        # 解码输出
        generated_ids = outputs.sequences[0][context_length:]
        generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        print(f"\n生成结果: {generated_text}")
        print(f"生成时间: {generation_time:.2f}秒")
        
        # 收集结果
        # 正确解码tokens
        token_ids = outputs.sequences[0].tolist()
        all_decoded_tokens = []
        for token_id in token_ids:
            # 解码单个token，去除空格
            decoded_token = tokenizer.decode([token_id], skip_special_tokens=False)
            # 处理特殊情况
            if decoded_token == '' or decoded_token == ' ':
                # 对于空token，尝试获取原始token表示
                raw_token = tokenizer.convert_ids_to_tokens([token_id])[0]
                all_decoded_tokens.append(raw_token)
            else:
                all_decoded_tokens.append(decoded_token)
        
        # 分离上下文tokens和生成的tokens
        context_tokens = all_decoded_tokens[:context_length]
        generated_tokens = all_decoded_tokens[context_length:]
        
        result = {
            "test_case": {
                "name": test_case['name'],
                "category": test_case['category'],
                "description": test_case['description'],
                "system_prompt": test_case['system_prompt'][:200] + "...",  # 截断以节省空间
                "user_prompt": test_case['user_prompt']
            },
            "context_length": context_length,
            "system_prompt_length": system_prompt_length,  # 保存系统提示长度
            "generated_text": generated_text,
            "generation_time": generation_time,
            "verification_results": [asdict(r) for r in verifier.verification_results],
            "tokens": all_decoded_tokens,  # 保留所有tokens用于完整显示
            "attention_heatmap": {
                "tokens": all_decoded_tokens,  # 包含所有tokens以便正确显示x轴
                "attention_weights": verifier.get_full_attention_matrix(),  # 只包含生成部分的注意力
                "context_boundary": context_length,
                "system_prompt_boundary": system_prompt_length,  # 新增：系统提示边界
                "generated_tokens": generated_tokens,  # 明确标记生成的tokens
                "context_tokens": context_tokens  # 明确标记上下文tokens
            }
        }
        
        # 打印验证结果摘要
        if verifier.verification_results:
            for vr in verifier.verification_results:
                print(f"\n📊 验证结果:")
                print(f"   序列: {vr.sequence}")
                print(f"   裁决: {vr.final_verdict}")
                print(f"   事实性得分: {vr.factuality_score:.2f}")
                print(f"   系统注意力 vs 用户注意力: {vr.avg_system_attention:.3f} vs {vr.avg_user_attention:.3f}")
                print(f"   预期行为: {test_case['expected_behavior']}")
        
        all_results.append(result)
    
    # 生成前端格式数据
    frontend_results = generate_frontend_format(all_results)
    
    # 直接保存到前端 public 目录
    frontend_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'public')
    os.makedirs(frontend_output_dir, exist_ok=True)
    
    output_file = os.path.join(frontend_output_dir, 'results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(frontend_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 验证完成！结果已保存到: {output_file}")
    
    # 打印总结
    print("\n📈 测试总结:")
    print(f"   测试用例数: {len(test_cases)}")
    
    # 按类别统计
    hallucination_cases = [tc for tc in test_cases if tc['category'] == 'hallucination']
    non_hallucination_cases = [tc for tc in test_cases if tc['category'] == 'non_hallucination']
    
    print(f"   - 幻觉生成测试: {len(hallucination_cases)} 个")
    print(f"   - 正常引用测试: {len(non_hallucination_cases)} 个")
    
    # 统计检测结果
    detected_sequences = sum(len(r['verification_results']) for r in all_results)
    detected_hallucinations = sum(
        1 for r in all_results 
        for vr in r['verification_results'] 
        if vr['is_hallucination']
    )
    
    print(f"\n   检测到的数字序列: {detected_sequences} 个")
    print(f"   检测为幻觉的序列: {detected_hallucinations} 个")
    

    
    return all_results


def generate_frontend_format(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """生成前端兼容的数据格式"""
    print("\n📄 生成前端数据格式...")
    
    frontend_results = []
    for result in results:
        # 如果有验证结果，为每个结果创建一个条目
        if result.get('verification_results'):
            for vr in result['verification_results']:
                frontend_result = {
                    "test_case": result['test_case'],
                    "context_length": result['context_length'],
                    "generated_text": result['generated_text'],
                    "verification_result": vr,
                    "attention_heatmap": result.get('attention_heatmap', {
                        "tokens": [],
                        "attention_weights": [],
                        "context_boundary": result['context_length'],
                        "system_prompt_boundary": result.get('system_prompt_length', 0)
                    })
                }
                frontend_results.append(frontend_result)
        else:
            # 如果没有检测到数字序列，添加一个默认结果
            frontend_result = {
                "test_case": result['test_case'],
                "context_length": result['context_length'],
                "generated_text": result['generated_text'],
                "verification_result": {
                    "sequence": "N/A",
                    "tokens": [],
                    "factuality_score": 1.0,
                    "avg_system_attention": 0.0,
                    "avg_user_attention": 0.0,
                    "final_verdict": "NO_SEQUENCE_DETECTED",
                    "is_hallucination": False,
                    "analyses": [],
                    "verdict_details": {}
                },
                "attention_heatmap": result.get('attention_heatmap', {
                    "tokens": [],
                    "attention_weights": [],
                    "context_boundary": result['context_length'],
                    "system_prompt_boundary": result.get('system_prompt_length', 0)
                })
            }
            frontend_results.append(frontend_result)
    
    return frontend_results


if __name__ == "__main__":
    import sys
    
    # 从命令行参数获取层索引（可选）
    attention_layer_index = -1  # 默认使用最后一层
    if len(sys.argv) > 1:
        try:
            attention_layer_index = int(sys.argv[1])
            print(f"使用命令行参数指定的注意力层索引: {attention_layer_index}")
        except ValueError:
            print(f"警告: 无效的层索引参数 '{sys.argv[1]}'，使用默认值 -1（最后一层）")
    
    # 运行验证
    results = run_verification(attention_layer_index=attention_layer_index)