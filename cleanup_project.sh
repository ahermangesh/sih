#!/bin/bash

# FloatChat Project Cleanup Script
# This script removes unnecessary files to free up disk space

echo "🧹 Starting FloatChat Project Cleanup..."

cd "/c/Users/KIIT0001/cursor projects/sih"

# 1. Clean up large log files (keep last 100 lines for reference)
echo "📄 Cleaning large log files..."
if [ -f "parallel_extract.log" ]; then
    tail -n 100 parallel_extract.log > temp_parallel.log
    mv temp_parallel.log parallel_extract.log
    echo "✅ Cleaned parallel_extract.log"
fi

if [ -f "processing_log.txt" ]; then
    tail -n 100 processing_log.txt > temp_processing.log
    mv temp_processing.log processing_log.txt
    echo "✅ Cleaned processing_log.txt"
fi

if [ -f "vector_index.log" ]; then
    tail -n 50 vector_index.log > temp_vector.log
    mv temp_vector.log vector_index.log
    echo "✅ Cleaned vector_index.log"
fi

# 2. Clean up Python cache files
echo "🐍 Removing Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
echo "✅ Removed Python cache files"

# 3. Clean up temporary files
echo "🗑️ Removing temporary files..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
echo "✅ Removed temporary files"

# 4. Clean up data cache (keep only essential processed data)
echo "💾 Cleaning data cache..."
if [ -d "data/cache" ]; then
    rm -rf data/cache/* 2>/dev/null || true
    echo "✅ Cleared data cache"
fi

# 5. Clean up old ARGO data (keep only 2024 and 2025)
echo "🌊 Cleaning old ARGO data (keeping 2024-2025)..."
if [ -d "argo_data" ]; then
    for year in 2020 2021 2022 2023; do
        if [ -d "argo_data/$year" ]; then
            rm -rf "argo_data/$year"
            echo "✅ Removed argo_data/$year"
        fi
    done
fi

# 6. Clean up duplicate virtual environments
echo "🐍 Cleaning duplicate virtual environments..."
if [ -d "venv" ] && [ -d ".venv" ]; then
    echo "Found both venv and .venv directories. Keeping .venv and removing venv..."
    rm -rf venv
    echo "✅ Removed duplicate venv directory"
fi

# 7. Clean up node_modules if not needed
echo "📦 Checking Node.js dependencies..."
cd floatchat-dashboard 2>/dev/null || true
if [ -d "node_modules" ]; then
    echo "ℹ️ Found node_modules directory. You can run 'npm install' to regenerate if needed."
    echo "To save space, you can delete it with: rm -rf floatchat-dashboard/node_modules"
fi
cd .. 2>/dev/null || true

# 8. Clean up Git objects (careful cleanup)
echo "🔧 Optimizing Git repository..."
git gc --prune=now 2>/dev/null || true
echo "✅ Git repository optimized"

# 9. Summary
echo ""
echo "🎉 Cleanup completed!"
echo ""
echo "📊 Space-saving actions taken:"
echo "   ✅ Truncated large log files"
echo "   ✅ Removed Python cache files"
echo "   ✅ Cleared temporary files"
echo "   ✅ Cleaned data cache"
echo "   ✅ Removed old ARGO data (2020-2023)"
echo "   ✅ Removed duplicate virtual environments"
echo "   ✅ Optimized Git repository"
echo ""
echo "💡 Additional space-saving tips:"
echo "   • Remove node_modules: rm -rf floatchat-dashboard/node_modules"
echo "   • Run 'npm install' in floatchat-dashboard when needed"
echo "   • Consider moving large datasets to external storage"
echo ""
echo "🔍 Check current disk usage with: du -sh *"