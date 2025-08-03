import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface AttentionDebugGraphProps {
  data: {
    attention_weights: number[][];
    system_prompt_boundary?: number;
    context_boundary: number;
    tokens?: string[];
  };
  sequenceStartPosition?: number; // Position where the number sequence started (if available)
}

export default function AttentionDebugGraph({ data, sequenceStartPosition }: AttentionDebugGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  
  useEffect(() => {
    if (!svgRef.current || !data || !data.attention_weights || data.attention_weights.length === 0) return;
    
    // Calculate max attention in system prompt region for each generated token
    const maxAttentions = data.attention_weights.map((row, i) => {
      // Find max attention in system prompt region (tokens 5 to system_prompt_boundary)
      let maxAttn = 0;
      const systemBoundary = data.system_prompt_boundary || data.context_boundary;
      for (let j = 5; j < Math.min(systemBoundary, row.length); j++) {
        if (row[j] > maxAttn) {
          maxAttn = row[j];
        }
      }
      return {
        position: i,
        maxAttention: maxAttn * 100, // Convert to percentage
      };
    });
    
    // Set up dimensions
    const margin = { top: 40, right: 60, bottom: 60, left: 80 };
    const width = 800 - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;
    
    // Clear previous content
    d3.select(svgRef.current).selectAll("*").remove();
    
    const svg = d3.select(svgRef.current)
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom);
    
    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);
    
    // Set up scales
    const xScale = d3.scaleLinear()
      .domain([0, maxAttentions.length - 1])
      .range([0, width]);
    
    const yScale = d3.scaleLinear()
      .domain([0, Math.max(20, ...maxAttentions.map(d => d.maxAttention))])
      .range([height, 0]);
    
    // Add axes
    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(xScale).ticks(10))
      .append("text")
      .attr("x", width / 2)
      .attr("y", 40)
      .attr("fill", "currentColor")
      .style("text-anchor", "middle")
      .text("Generated Token Position");
    
    g.append("g")
      .call(d3.axisLeft(yScale))
      .append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", -50)
      .attr("x", -height / 2)
      .attr("fill", "currentColor")
      .style("text-anchor", "middle")
      .text("Max System Attention (%)");
    
    // Add title
    svg.append("text")
      .attr("x", (width + margin.left + margin.right) / 2)
      .attr("y", 20)
      .attr("text-anchor", "middle")
      .style("font-size", "16px")
      .style("font-weight", "bold")
      .text("Max Attention to System Prompt per Generated Token");
    
    // Add 10% threshold line
    g.append("line")
      .attr("x1", 0)
      .attr("y1", yScale(10))
      .attr("x2", width)
      .attr("y2", yScale(10))
      .attr("stroke", "#ef4444")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "5,5");
    
    // Add threshold label
    g.append("text")
      .attr("x", width - 5)
      .attr("y", yScale(10) - 5)
      .attr("text-anchor", "end")
      .attr("fill", "#ef4444")
      .style("font-size", "12px")
      .style("font-weight", "bold")
      .text("10% Threshold");
    
    // Add sequence start marker if provided
    if (sequenceStartPosition !== undefined && sequenceStartPosition >= 0 && sequenceStartPosition < maxAttentions.length) {
      g.append("line")
        .attr("x1", xScale(sequenceStartPosition))
        .attr("y1", 0)
        .attr("x2", xScale(sequenceStartPosition))
        .attr("y2", height)
        .attr("stroke", "#3b82f6")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "3,3");
      
      g.append("text")
        .attr("x", xScale(sequenceStartPosition) + 5)
        .attr("y", 20)
        .attr("fill", "#3b82f6")
        .style("font-size", "12px")
        .style("font-weight", "bold")
        .text("Number sequence start");
    }
    
    // Create line generator
    const line = d3.line<{position: number, maxAttention: number}>()
      .x(d => xScale(d.position))
      .y(d => yScale(d.maxAttention));
    
    // Add the line
    g.append("path")
      .datum(maxAttentions)
      .attr("fill", "none")
      .attr("stroke", "#10b981")
      .attr("stroke-width", 2)
      .attr("d", line);
    
    // Add dots
    g.selectAll(".dot")
      .data(maxAttentions)
      .enter().append("circle")
      .attr("class", "dot")
      .attr("cx", d => xScale(d.position))
      .attr("cy", d => yScale(d.maxAttention))
      .attr("r", 4)
      .attr("fill", d => d.maxAttention > 10 ? "#10b981" : "#ef4444");
    
    // Add tooltip
    const tooltip = d3.select("body").append("div")
      .attr("class", "attention-debug-tooltip")
      .style("opacity", 0)
      .style("position", "absolute")
      .style("background", "rgba(0, 0, 0, 0.8)")
      .style("color", "white")
      .style("padding", "8px")
      .style("border-radius", "4px")
      .style("font-size", "12px");
    
    g.selectAll(".dot")
      .on("mouseover", function(event, d) {
        tooltip.transition()
          .duration(200)
          .style("opacity", .9);
        tooltip.html(`Token ${d.position}<br/>Max Attention: ${d.maxAttention.toFixed(2)}%`)
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY - 28) + "px");
      })
      .on("mouseout", function() {
        tooltip.transition()
          .duration(500)
          .style("opacity", 0);
      });
    
    // Cleanup function
    return () => {
      d3.select("body").selectAll(".attention-debug-tooltip").remove();
    };
  }, [data, sequenceStartPosition]);
  
  if (!data || !data.attention_weights || data.attention_weights.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-100 dark:bg-gray-900 rounded-lg">
        <p className="text-gray-500">暂无调试数据</p>
      </div>
    );
  }
  
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">注意力调试图表</h3>
      <div className="overflow-x-auto">
        <svg ref={svgRef}></svg>
      </div>
      <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
        <p>• 绿色点：注意力 &gt; 10%（非幻觉）</p>
        <p>• 红色点：注意力 ≤ 10%（可能是幻觉）</p>
        <p>• 蓝色虚线：数字序列开始位置</p>
        <p>• 红色虚线：10% 阈值线</p>
      </div>
    </div>
  );
}