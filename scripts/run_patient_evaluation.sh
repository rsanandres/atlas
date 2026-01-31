#!/bin/bash

# Patient-Oriented RAGAS Evaluation Runner
# Runs evaluation on the new 20-question patient-oriented testset.
# Uses the same retry logic as the original batch script.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTSET="$PROJECT_ROOT/POC_RAGAS/data/testsets/patient_oriented_testset_20.json"

# Output directory with timestamp
if [ -z "$BATCH_OUTPUT_DIR" ]; then
    OUTPUT_DIR="$PROJECT_ROOT/POC_RAGAS/data/testsets/batch_runs/patient_run_$(date -u +%Y%m%dT%H%M%SZ)"
else
    OUTPUT_DIR="$BATCH_OUTPUT_DIR"
fi

# Range configuration (defaults to all 20 questions)
START_INDEX=${START_INDEX:-0}
END_INDEX=${END_INDEX:-20}
MAX_RETRIES=${MAX_RETRIES:-3}

echo "=================================================="
echo "Patient-Oriented RAGAS Evaluation"
echo "=================================================="
echo "Testset: $TESTSET"
echo "Output:  $OUTPUT_DIR"
echo "Range:   Q[$START_INDEX] to Q[$END_INDEX]"
echo ""

mkdir -p "$OUTPUT_DIR"

# Detect Python
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
    echo "Using venv python: $PYTHON_CMD"
else
    PYTHON_CMD="python3"
    echo "Using system python: $PYTHON_CMD"
fi

# Track stats
TOTAL=0
SUCCESS=0
FAILED=0
SKIPPED=0

for ((i=START_INDEX; i<END_INDEX; i++)); do
    TOTAL=$((TOTAL + 1))
    
    # Resume check: Skip if result already exists
    RESULT_FILE="$OUTPUT_DIR/result_$(printf "%03d" $i).json"
    if [ -f "$RESULT_FILE" ]; then
        echo "⏭️  Skipping Q[$i] (Already completed)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo "=================================================="
    echo "📋 Question $i / $((END_INDEX-1))"
    echo "=================================================="
    
    RETRY_COUNT=0
    
    # Retry loop for this question
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        # 1. Start API Service
        echo "🚀 Starting API service..."
        $PYTHON_CMD api/main.py > "$OUTPUT_DIR/api_log_$i.txt" 2>&1 &
        API_PID=$!
        
        # Wait for API to be ready
        echo "⏳ Waiting for API initialization (30s)..."
        sleep 30
        
        # 2. Run Single Evaluation Question
        echo "🔍 Running evaluation..."
        $PYTHON_CMD "$PROJECT_ROOT/POC_RAGAS/scripts/run_evaluation_batch.py" \
            --testset "$TESTSET" \
            --question-index "$i" \
            --output-dir "$OUTPUT_DIR" \
            --mode api \
            --patient-mode both
            
        EXIT_CODE=$?
            
        # 3. Kill API Service
        echo "🛑 Stopping API service (PID: $API_PID)..."
        kill $API_PID 2>/dev/null
        wait $API_PID 2>/dev/null
        pkill -f "api/main.py" 2>/dev/null
        
        # Check exit code
        if [ $EXIT_CODE -eq 0 ]; then
            echo "✅ Q[$i] completed successfully"
            SUCCESS=$((SUCCESS + 1))
            break
        elif [ $EXIT_CODE -eq 2 ]; then
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo "⚠️  500 Error detected. Retry $RETRY_COUNT of $MAX_RETRIES..."
            sleep 30
        else
            echo "❌ Q[$i] failed with exit code $EXIT_CODE"
            FAILED=$((FAILED + 1))
            break
        fi
        
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "❌ Q[$i] failed after $MAX_RETRIES retries"
            FAILED=$((FAILED + 1))
        fi
    done
    
    # Brief pause between questions
    sleep 3
done

echo ""
echo "=================================================="
echo "📊 EVALUATION COMPLETE"
echo "=================================================="
echo "Total:   $TOTAL questions"
echo "Success: $SUCCESS"
echo "Failed:  $FAILED"  
echo "Skipped: $SKIPPED"
echo "Results: $OUTPUT_DIR"
echo "=================================================="
