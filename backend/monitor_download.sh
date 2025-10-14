#!/bin/bash
while true; do
    count=$(ls -1 /app/backend/validation_data_large/*_price_data.csv 2>/dev/null | wc -l)
    echo "$(date '+%H:%M:%S') - Downloaded: $count/208 stocks"
    
    if [ $count -ge 208 ]; then
        echo "Download complete!"
        break
    fi
    
    if ! ps aux | grep -v grep | grep large_scale_data_downloader > /dev/null; then
        echo "Process stopped. Checking log..."
        tail -20 /app/backend/large_download.log
        break
    fi
    
    sleep 30
done
