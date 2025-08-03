import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface AttentionHeatmapProps {
  data: {
    tokens: string[];
    attention_weights: number[][];
    context_boundary: number;
    system_prompt_boundary?: number;  // 新增：系统提示边界
    generated_tokens?: string[];
    context_tokens?: string[];
  };
  analyses: Array<{
    token: string;
    attention_position?: number;
    legitimate_score?: number;
    factuality_score?: number;  // 新增：事实性得分
    system_attention?: number;   // 新增：系统注意力
    user_attention?: number;     // 新增：用户注意力
  }>;
}

export default function AttentionHeatmap({ data, analyses }: AttentionHeatmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800 });

  useEffect(() => {
    if (!containerRef.current) return;
    
    const resizeObserver = new ResizeObserver(entries => {
      for (let entry of entries) {
        const { width } = entry.contentRect;
        setDimensions({ width: width - 40 });
      }
    });
    
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current || !data || !data.attention_weights || data.attention_weights.length === 0) return;
    
    console.log('AttentionHeatmap data:', {
      tokens_count: data.tokens?.length,
      weights_count: data.attention_weights?.length,
      context_boundary: data.context_boundary,
      generated_tokens: data.generated_tokens,
      analyses_count: analyses?.length
    });

    const margin = { top: 50, right: 120, bottom: 150, left: 150 }; // 增加左边距以容纳Y轴标签
    const numRows = data.attention_weights.length;
    // numCols should be the total number of tokens, not just the first row length
    const numCols = data.tokens.length;
    
    // 方形单元格 - 宽高相同
    const cellSize = 12; // 固定尺寸，保证是正方形
    const width = numCols * cellSize;
    const height = numRows * cellSize; // 高度根据行数动态计算
    const svgWidth = width + margin.left + margin.right;
    const svgHeight = height + margin.top + margin.bottom; // 动态SVG高度

    // 清除之前的内容
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("width", svgWidth)
      .attr("height", svgHeight);

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // 创建比例尺
    const xScale = d3.scaleBand()
      .domain(d3.range(numCols).map(String))
      .range([0, width])
      .padding(0);  // 无间距，保证方块紧密排列

    const yScale = d3.scaleBand()
      .domain(d3.range(numRows).map(String))
      .range([0, height])
      .padding(0);  // 无间距，保证方块紧密排列

    // 归一化注意力权重 - 处理三角形模式
    const normalizedData = data.attention_weights.map((row, i) => {
      const maxValue = Math.max(...row.filter(v => v > 0));
      const minValue = Math.min(...row.filter(v => v > 0));
      const range = maxValue - minValue || 1;
      
      // 只处理实际存在的注意力值（三角形模式）
      // 第i行应该有 context_boundary + i + 1 个值
      const expectedLength = data.context_boundary + i + 1;
      const actualLength = Math.min(row.length, expectedLength);
      
      if (i === 0) {
        console.log(`Row ${i}: expected ${expectedLength}, actual ${row.length}, using ${actualLength}`);
      }
      
      return row.slice(0, actualLength).map((value, j) => ({
        row: i,
        col: j,
        value: value || 0,
        normalizedValue: value > 0 ? (value - minValue) / range : 0,
        originalValue: value
      }));
    }).flat();
    
    console.log('Normalized data cells:', normalizedData.length);
    console.log('Last few cells:', normalizedData.slice(-5));

    // 颜色比例尺 - 使用归一化后的值
    const colorScale = d3.scaleSequential(d3.interpolateViridis)
      .domain([0, 1]);

    // 添加背景以显示三角形边界
    // 为每个不应该有值的位置添加灰色背景
    const triangleBoundary = [];
    for (let row = 0; row < numRows; row++) {
      const maxCol = data.context_boundary + row + 1;
      for (let col = maxCol; col < numCols; col++) {
        triangleBoundary.push({ row, col });
      }
    }
    
    console.log('Triangle boundary cells:', triangleBoundary.length);
    console.log('First few boundary cells:', triangleBoundary.slice(0, 5));
    
    // 绘制三角形边界背景
    g.selectAll(".boundary-cell")
      .data(triangleBoundary)
      .enter().append("rect")
      .attr("class", "boundary-cell")
      .attr("x", d => xScale(String(d.col))!)
      .attr("y", d => yScale(String(d.row))!)
      .attr("width", xScale.bandwidth())
      .attr("height", yScale.bandwidth())
      .attr("fill", "#e5e7eb")  // Fixed gray color
      .attr("opacity", 0.4)
      .attr("stroke", "#d1d5db")
      .attr("stroke-width", 0.5)
      .attr("rx", 0);  // 无圆角，保持方形

    // 创建热力图单元格
    const cells = g.selectAll(".cell")
      .data(normalizedData)
      .enter().append("rect")
      .attr("class", "cell heatmap-cell")
      .attr("x", d => xScale(String(d.col))!)
      .attr("y", d => yScale(String(d.row))!)
      .attr("width", xScale.bandwidth())
      .attr("height", yScale.bandwidth())
      .attr("fill", d => colorScale(d.normalizedValue))
      .attr("rx", 0)  // 无圆角，保持方形
      .style("cursor", "pointer");

    // 添加边界线和区域标签
    if (data.system_prompt_boundary && data.system_prompt_boundary > 0) {
      const systemBoundaryX = xScale(String(data.system_prompt_boundary))! - xScale.bandwidth() / 2;
      
      // 系统提示边界线
      g.append("line")
        .attr("class", "system-boundary")
        .attr("x1", systemBoundaryX)
        .attr("y1", -10)
        .attr("x2", systemBoundaryX)
        .attr("y2", height + 10)
        .attr("stroke", "#3b82f6")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "3,3");
    }
    
    if (data.context_boundary > 0) {
      const contextBoundaryX = xScale(String(data.context_boundary))! - xScale.bandwidth() / 2;
      
      // 上下文边界线
      g.append("line")
        .attr("class", "context-boundary")
        .attr("x1", contextBoundaryX)
        .attr("y1", -10)
        .attr("x2", contextBoundaryX)
        .attr("y2", height + 10)
        .attr("stroke", "#ef4444")
        .attr("stroke-width", 3)
        .attr("stroke-dasharray", "5,5");

      // 添加区域标签
      const systemBoundaryX = data.system_prompt_boundary ? 
        xScale(String(data.system_prompt_boundary))! - xScale.bandwidth() / 2 : 0;
      
      // 系统提示区域标签
      if (data.system_prompt_boundary && data.system_prompt_boundary > 0) {
        g.append("text")
          .attr("x", systemBoundaryX / 2)
          .attr("y", -20)
          .attr("text-anchor", "middle")
          .attr("fill", "#10b981")
          .attr("font-weight", "bold")
          .text("系统提示");
        
        // 用户提示区域标签
        g.append("text")
          .attr("x", systemBoundaryX + (contextBoundaryX - systemBoundaryX) / 2)
          .attr("y", -20)
          .attr("text-anchor", "middle")
          .attr("fill", "#3b82f6")
          .attr("font-weight", "bold")
          .text("用户提示");
      } else {
        // 如果没有系统提示边界，显示原始标签
        g.append("text")
          .attr("x", contextBoundaryX / 2)
          .attr("y", -20)
          .attr("text-anchor", "middle")
          .attr("fill", "#10b981")
          .attr("font-weight", "bold")
          .text("原始上下文");
      }

      // 生成内容区域标签
      g.append("text")
        .attr("x", contextBoundaryX + (width - contextBoundaryX) / 2)
        .attr("y", -20)
        .attr("text-anchor", "middle")
        .attr("fill", "#ef4444")
        .attr("font-weight", "bold")
        .text("生成内容");
    }
    
    // 添加三角形边界线
    const trianglePath = d3.line()
      .x((d: any) => xScale(String(d.col))! + xScale.bandwidth() / 2)
      .y((d: any) => yScale(String(d.row))! + yScale.bandwidth() / 2);
    
    const boundaryPoints = [];
    for (let row = 0; row < numRows; row++) {
      const maxCol = data.context_boundary + row;
      boundaryPoints.push({ row, col: maxCol });
    }
    // 添加最后一个点以闭合路径
    if (numRows > 0) {
      boundaryPoints.push({ row: numRows - 1, col: numCols - 1 });
      boundaryPoints.push({ row: 0, col: numCols - 1 });
    }
    
    g.append("path")
      .datum(boundaryPoints)
      .attr("class", "triangle-boundary")
      .attr("d", trianglePath)
      .attr("fill", "none")
      .attr("stroke", "#666")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "5,5")
      .attr("opacity", 0.5);

    // 添加X轴标签（tokens）
    const xAxis = g.append("g")
      .attr("transform", `translate(0,${height})`);

    xAxis.selectAll("text")
      .data(data.tokens)
      .enter().append("text")
      .attr("x", (d, i) => xScale(String(i))! + xScale.bandwidth() / 2)
      .attr("y", 15)
      .attr("text-anchor", "start")  // Changed to start for rotated text
      .attr("font-size", "10px")
      .attr("fill", "#374151")  // Direct color
      .style("fill", "#374151")  // Ensure fill is applied
      .attr("transform", (d, i) => `rotate(45,${xScale(String(i))! + xScale.bandwidth() / 2},15)`)
      .text(d => d.length > 10 ? d.substring(0, 10) + "..." : d);

    // 添加Y轴标签（生成的tokens）
    const yAxis = g.append("g");
    
    // 使用generated_tokens如果可用，否则从analyses中提取
    const yAxisLabels = data.generated_tokens || 
      data.tokens.slice(data.context_boundary) || 
      analyses.map(a => a.token);
    
    console.log('Y-axis labels:', yAxisLabels);
    console.log('Y-scale domain:', yScale.domain());
    console.log('numRows:', numRows, 'numCols:', numCols);
    
    // Safety check
    if (!yAxisLabels || yAxisLabels.length === 0) {
      console.error('No Y-axis labels available!');
    }

    const yTexts = yAxis.selectAll("text")
      .data(yAxisLabels)
      .enter().append("text")
      .attr("x", -10)
      .attr("y", (d, i) => {
        const y = yScale(String(i))! + yScale.bandwidth() / 2;
        console.log(`Y-axis label ${i} "${d}" at y=${y}`);
        return y;
      })
      .attr("text-anchor", "end")
      .attr("dominant-baseline", "middle")
      .attr("font-size", "12px")
      .attr("fill", "#374151")  // Direct color instead of currentColor
      .style("fill", "#374151")  // Ensure fill is applied
      .text(d => d);
      
    console.log('Y-axis text elements created:', yTexts.size());

    // 添加颜色图例
    const legendWidth = 20;
    const legendHeight = Math.min(200, height * 0.8); // 确保图例不超过热力图高度的80%
    const legendScale = d3.scaleLinear()
      .domain([0, 1])
      .range([legendHeight, 0]);

    // 将图例放置在热力图右侧，垂直居中
    const legendX = width + margin.left + 20; // 热力图右侧20px处
    const legendY = margin.top + (height - legendHeight) / 2; // 垂直居中
    
    const legend = svg.append("g")
      .attr("transform", `translate(${legendX}, ${legendY})`);

    // 创建渐变
    const defs = svg.append("defs");
    const gradient = defs.append("linearGradient")
      .attr("id", "legend-gradient")
      .attr("x1", "0%")
      .attr("y1", "100%")
      .attr("x2", "0%")
      .attr("y2", "0%");

    const numStops = 10;
    for (let i = 0; i <= numStops; i++) {
      gradient.append("stop")
        .attr("offset", `${(i / numStops) * 100}%`)
        .attr("stop-color", colorScale(i / numStops));
    }

    // 添加图例标题
    legend.append("text")
      .attr("x", legendWidth / 2)
      .attr("y", -10)
      .attr("text-anchor", "middle")
      .attr("font-size", "12px")
      .attr("font-weight", "bold")
      .text("注意力权重");

    legend.append("rect")
      .attr("width", legendWidth)
      .attr("height", legendHeight)
      .style("fill", "url(#legend-gradient)");

    legend.append("g")
      .attr("transform", `translate(${legendWidth}, 0)`)
      .call(d3.axisRight(legendScale).ticks(5)
        .tickFormat(d => `${(d * 100).toFixed(0)}%`));

    // 添加工具提示
    const tooltip = d3.select("body").append("div")
      .attr("class", "custom-tooltip")
      .style("opacity", 0)
      .style("position", "absolute");

    cells
      .on("mouseover", function(event, d) {
        tooltip.transition()
          .duration(200)
          .style("opacity", .9);
        
        // 获取生成的token
        const generatedTokens = data.generated_tokens || data.tokens.slice(data.context_boundary);
        const tokenFrom = generatedTokens[d.row] || analyses[d.row]?.token || `Token ${d.row}`;
        const tokenTo = data.tokens[d.col] || `Token ${d.col}`;
        const isContext = d.col < data.context_boundary;
        
        // 检查是否在三角形边界内
        const isWithinTriangle = d.col <= data.context_boundary + d.row;
        
        tooltip.html(`
          <div>
            <strong>${tokenFrom} → ${tokenTo}</strong><br/>
            原始权重: ${(d.originalValue * 100).toFixed(4)}%<br/>
            归一化值: ${(d.normalizedValue * 100).toFixed(2)}%<br/>
            来源: ${isContext ? '✅ 上下文' : '❌ 生成内容'}
          </div>
        `)
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY - 28) + "px");
      })
      .on("mouseout", function() {
        tooltip.transition()
          .duration(500)
          .style("opacity", 0);
      });

    return () => {
      d3.select("body").selectAll(".custom-tooltip").remove();
    };
  }, [data, analyses, dimensions]);

  if (!data || !data.attention_weights || data.attention_weights.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-100 dark:bg-gray-900 rounded-lg">
        <p className="text-gray-500">暂无注意力数据</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-xs text-gray-500 dark:text-gray-500">
          * 颜色基于归一化注意力权重 | 三角形模式显示因果注意力（每个token只能看到之前的token）
        </div>
      </div>
      <div 
        ref={scrollContainerRef}
        className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg"
      >
        <svg ref={svgRef}></svg>
      </div>
    </div>
  );
}