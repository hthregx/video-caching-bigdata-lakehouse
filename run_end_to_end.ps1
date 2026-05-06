param(
    [switch]$LaunchDemo
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "VIDEO CACHING BIG DATA END-TO-END RUN"
Write-Host "========================================"

# Ensure running from project root
Set-Location $PSScriptRoot

# Input check
$inputFile = "data/processed/clean_video_logs.csv"

if (!(Test-Path $inputFile)) {
    Write-Host "ERROR: Missing input file: $inputFile" -ForegroundColor Red
    Write-Host "Please put clean_video_logs.csv into data/processed/ first."
    exit 1
}

# Prepare folders
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null
New-Item -ItemType Directory -Force -Path "outputs/charts" | Out-Null

# Optional Spark memory config for PySpark full run
$env:PYSPARK_SUBMIT_ARGS = "--driver-memory 8g --conf spark.driver.maxResultSize=2g pyspark-shell"

Write-Host ""
Write-Host "[1/5] Running Spark feature engineering..."
python spark/03_stream_features_spark.py

Write-Host ""
Write-Host "[2/5] Running full hot video prediction..."
python spark/04_hot_video_prediction_spark_full.py

Write-Host ""
Write-Host "[3/5] Exporting all hot videos and top hot videos..."
python spark/04b_export_top_hot_videos_spark.py

Write-Host ""
Write-Host "[4/5] Running cache recommendation and evaluation..."
python spark/05_cache_recommendation_evaluation.py

Write-Host ""
Write-Host "[5/5] Validating final outputs..."
python -c "import pandas as pd; from pathlib import Path; files=['outputs/video_features.csv','outputs/hot_video_predictions.csv','outputs/all_hot_videos.csv','outputs/top_hot_videos.csv','outputs/cache_recommendation.csv','outputs/evaluation_metrics.csv']; print('===== FILE CHECK ====='); [print(f, Path(f).exists(), Path(f).stat().st_size if Path(f).exists() else 0) for f in files]; feat=pd.read_csv('outputs/video_features.csv'); pred=pd.read_csv('outputs/hot_video_predictions.csv'); cache=pd.read_csv('outputs/cache_recommendation.csv'); print('\n===== FINAL SUMMARY ====='); print('Feature rows:', len(feat)); print('Prediction rows:', len(pred)); print('Cache rows:', len(cache)); print('Sum views_count:', feat['views_count'].sum()); print('\nHOT counts:'); print(pred['hot_label'].value_counts()); print('\nCache decisions:'); print(cache['cache_decision'].value_counts())"

Write-Host ""
Write-Host "========================================"
Write-Host "END-TO-END PIPELINE FINISHED"
Write-Host "========================================"

Write-Host ""
Write-Host "Main outputs:"
Write-Host "- outputs/video_features.csv"
Write-Host "- outputs/hot_video_predictions.csv"
Write-Host "- outputs/all_hot_videos.csv"
Write-Host "- outputs/top_hot_videos.csv"
Write-Host "- outputs/cache_recommendation.csv"
Write-Host "- outputs/evaluation_metrics.csv"
Write-Host "- outputs/charts/"

if ($LaunchDemo) {
    Write-Host ""
    Write-Host "Launching Mini CDN API server and Streamlit dashboard..."

    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python scripts/mini_cdn_server.py"
    Start-Sleep -Seconds 5
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python -m streamlit run scripts/mini_cdn_dashboard.py"

    Write-Host ""
    Write-Host "Mini CDN API: http://127.0.0.1:8000"
    Write-Host "Mini CDN Dashboard: http://localhost:8501"
}