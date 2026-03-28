#!/bin/bash

echo ""
echo " ============================================="
echo "   CLP Rat Tracker - Conditioned Place Preference"
echo " ============================================="
echo ""

cd "$(dirname "$0")"

# ---- Check for Python 3 ----
if command -v python3 &> /dev/null; then
    PYTHON=python3
    PIP=pip3
elif command -v python &> /dev/null; then
    PYTHON=python
    PIP=pip
else
    echo " [ERROR] Python 3 is not installed on this computer."
    echo ""
    echo " To install Python:"
    echo "   Option 1: Go to https://www.python.org/downloads/"
    echo "   Option 2: Open Terminal and run: brew install python"
    echo ""
    read -p " Press Enter to exit..."
    exit 1
fi

echo " [OK] Python found."
$PYTHON --version
echo ""

# ---- Create virtual environment if it doesn't exist ----
if [ ! -f "venv/bin/python" ]; then
    echo " Creating virtual environment..."
    $PYTHON -m venv venv
    if [ $? -ne 0 ]; then
        echo " [WARNING] Could not create virtual environment."
        echo " Installing packages globally instead..."
        $PIP install -r requirements.txt
        $PYTHON main.py
        exit $?
    fi
    echo " [OK] Virtual environment created."
    echo ""
fi

# ---- Activate virtual environment ----
source venv/bin/activate

# ---- Install/update dependencies ----
echo " Checking dependencies..."
python -c "import cv2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo " Installing required packages (this may take a minute)..."
    echo ""
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo ""
        echo " [ERROR] Failed to install packages."
        echo " Try running manually:"
        echo "   pip3 install -r requirements.txt"
        echo ""
        read -p " Press Enter to exit..."
        exit 1
    fi
    echo ""
    echo " [OK] All packages installed."
    echo ""
fi

# ---- Launch the app ----
echo " Starting CLP Rat Tracker..."
echo ""
python main.py
if [ $? -ne 0 ]; then
    echo ""
    echo " [ERROR] The application encountered an error."
    echo ""
    echo " Try these steps:"
    echo "   1. Run: pip3 install -r requirements.txt"
    echo "   2. Run: python3 main.py"
    echo ""
    read -p " Press Enter to exit..."
fi
