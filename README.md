# Airware – Autonomous AQI Intelligence System

Airware is an agent-driven Air Quality Intelligence System designed to proactively protect users from harmful pollution levels. Instead of simply reporting AQI values after conditions have worsened, Airware continuously monitors, predicts, interprets, and advises — transforming raw air-quality data into meaningful actions that help users stay safer every day.

## Problem Overview

India is facing some of the worst air-quality levels globally. Cities like Delhi, Kolkata, Mumbai, and Lucknow repeatedly enter Very Poor, Severe, and Hazardous AQI ranges. PM2.5 concentrations often exceed safe limits by 10–20×, making routine breathing a legitimate health risk.

This crisis is driven by:

- Vehicular emissions
- Industrial pollution
- Crop residue burning
- Construction dust
- Winter stagnation and poor dispersion

### Health impact

Exposure to toxic particulate matter has immediate and long-term consequences:

- PM2.5 enters the bloodstream, harming lungs, heart, and cognitive function
- Children, the elderly, and people with asthma face dangerous flare-ups and hospitalisations
- Even healthy adults experience headaches, fatigue, reduced lung capacity, and inflammation
- Long-term exposure reduces life expectancy across India

Despite this, most people rely on passive dashboards or delayed government updates that only describe how bad things already are.

## Why Agents?

Air pollution is a fast-changing, multi-stage, high-risk problem. Autonomous agents enable a full end-to-end, intelligent, responsive system.

### 1. Real-Time Monitoring Agent
Tracks live AQI, detects rises, and triggers alerts.

### 2. Analytical & Interpretation Agent (Gemini)
Processes AQI data into structured JSON including risks, pollutant contributions, and health impacts.

### 3. Recommendation Agent
Provides actionable, personalized guidance.

### 4. Simulation & Scenario Agent
Helps users plan safer activities and timings.

## What We Built

Airware combines these agents to create an autonomous AQI companion:

- Real-time AQI tracking  
- Forecasting & analysis  
- Personalized recommendations  
- Scenario simulation  
- Live alerts and updates  

## Technology Stack

- **APIs:** WAQI, OpenAQ  
- **Backend:** Flask, Socket.IO, CORS, MySQL  
- **Intelligence:** Gemini Agents  
- **Frontend:** HTML/CSS/JS  

## Demo

GitHub: https://github.com/SohamMukherjee2011/Airware_Final_Submission

## If Given More Time

- ML-based AQI Predictor  
- Automatic alerting on predicted spikes  
- Smart air purifier integration  

## Project Structure

```
Airware/
│
├── backend/
│   ├── app.py
│   ├── database/
│   ├── agents/
│   ├── sockets/
│
├── frontend/
│   ├── static/
│   ├── templates/
│   ├── js/
│   ├── css/
│
└── README.md
```
