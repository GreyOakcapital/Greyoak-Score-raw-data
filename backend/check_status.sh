#!/bin/bash
echo "=============================================================="
echo "  GREYOAK VALIDATION - REAL-TIME STATUS"
echo "=============================================================="
echo ""
echo "Current Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Download progress
downloaded=$(ls -1 /app/backend/validation_data_large/*_price_data.csv 2>/dev/null | wc -l)
target=208
progress=$((downloaded * 100 / target))

echo "📊 DOWNLOAD PROGRESS:"
echo "   Downloaded: $downloaded / $target stocks ($progress%)"
echo "   Data dir: /app/backend/validation_data_large/"
echo ""

# Process status
if ps aux | grep -v grep | grep large_scale_data_downloader > /dev/null; then
    echo "   Status: ✅ Download process running"
else
    echo "   Status: ⚠️  Download process stopped"
fi
echo ""

# Validation status
if ps aux | grep -v grep | grep auto_validate_after_download > /dev/null; then
    echo "🔍 VALIDATION MONITOR:"
    echo "   Status: ✅ Monitoring active"
    echo ""
    echo "   Latest update:"
    tail -3 /app/backend/auto_validation.log 2>/dev/null
else
    echo "🔍 VALIDATION MONITOR:"
    echo "   Status: ⚠️  Not running"
fi
echo ""

# Output files
echo "📁 OUTPUT FILES:"
if [ -f "/app/backend/greyoak_scores_2019_2022.csv" ]; then
    scores=$(wc -l < /app/backend/greyoak_scores_2019_2022.csv)
    echo "   ✅ Scores: $scores records"
else
    echo "   ⏳ Scores: Not yet generated"
fi

if [ -f "/app/backend/stock_prices_2019_2022.csv" ]; then
    prices=$(wc -l < /app/backend/stock_prices_2019_2022.csv)
    echo "   ✅ Prices: $prices records"
else
    echo "   ⏳ Prices: Not yet generated"
fi

if [ -f "/app/backend/stock_fundamentals_2019_2022.csv" ]; then
    funds=$(wc -l < /app/backend/stock_fundamentals_2019_2022.csv)
    echo "   ✅ Fundamentals: $funds records"
else
    echo "   ⏳ Fundamentals: Not yet generated"
fi

echo ""
echo "=============================================================="
echo ""

# Estimated completion
if [ $downloaded -lt $target ]; then
    remaining=$((target - downloaded))
    minutes=$((remaining * 3 / 60))
    echo "⏱️  Estimated completion: ~$minutes minutes"
else
    echo "✅ Download complete - validation should be running or complete"
fi

echo ""
echo "To view live logs:"
echo "  Download: tail -f /app/backend/large_download.log"
echo "  Validation: tail -f /app/backend/auto_validation.log"
echo "=============================================================="
