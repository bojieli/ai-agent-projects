#!/bin/bash

echo "🚀 启动事实一致性校验器系统..."

# 检查是否已经生成验证结果
if [ ! -f "frontend/public/results.json" ]; then
    echo "📊 运行验证测试..."
    cd backend
    python verifier.py
    cd ..
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 启动前端开发服务器
echo "🌐 启动前端开发服务器..."
echo "📍 请访问 http://localhost:3000"
cd frontend
npm run dev