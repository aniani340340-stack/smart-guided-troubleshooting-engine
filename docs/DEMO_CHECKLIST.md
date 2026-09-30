# Samsung Smart Guided Troubleshooting Engine — Live Demo Checklist

**Hackathon Presentation Checklist & Verification Runbook**

---

## 1. PRE-DEMO CHECKLIST (T-Minus 10 Minutes)

- [ ] **1. Backend Server Running:**
  - Command: `python theme02_troubleshooting_engine/run_server.py`
  - Verify terminal output: `PaddleOCR pre-warmed successfully at startup in 492.15 ms.`
  - Port: `8000` (`http://127.0.0.1:8000`)
- [ ] **2. Backend Health Verification:**
  - Run: `curl http://127.0.0.1:8000/health`
  - Expected output: `{"status": "ok"}`
- [ ] **3. Frontend Dev Server Running:**
  - Command: `cd frontend && npm run dev`
  - Port: `5173` (`http://localhost:5173`)
- [ ] **4. API URL Configuration:**
  - Verify `frontend/src/services/api.ts` targets `http://127.0.0.1:8000` (eliminates Windows DNS latency).
- [ ] **5. Browser Window Prepared:**
  - Open Chrome/Edge at `http://localhost:5173` in Fullscreen / Presentation Mode.
  - Clear any active sessions by clicking the **"Galaxy Support"** logo or refresh button.
- [ ] **6. Primary Demo Query Prepared on Clipboard:**
  - `"My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect."`
- [ ] **7. Multimodal Screenshot Ready (Optional Deep-Dive):**
  - Path: `test_images/realistic_screenshot.png` (Contains Samsung Bluetooth dialog + code `BT-204`).
- [ ] **8. Backup Scenarios Verified:**
  - Wi-Fi Only: `"My Wi-Fi keeps disconnecting"`
  - Bluetooth Only: `"My Bluetooth earbuds won't connect"`
  - Error Code: Manual error code `1001` or `BT-204`

---

## 2. LIVE DEMO CHECKLIST (Stage Presentation)

- [ ] **1. Introduction & Context:**
  - State Theme 02 problem (static FAQs vs multi-intent customer friction).
- [ ] **2. Submit Primary Query:**
  - Paste query: `"My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect."`
  - Click **"Start Diagnosis"**.
- [ ] **3. Verify Intent Decomposition:**
  - Point out Intent Tabs: `[NETWORK]` and `[BLUETOOTH]`.
  - Point out confidence score (95%) and technical problem description.
- [ ] **4. Demonstrate Deeplink Action:**
  - Point to **"Target Setting: Settings → Connections → Wi-Fi"**.
  - Click **"OPEN SETTINGS →"** and observe toast confirmation.
- [ ] **5. Demonstrate Simulated Telemetry:**
  - Point to the **Verification Panel** showing active simulated sensor state.
- [ ] **6. Demonstrate Step Progression:**
  - Click **"Step Worked / Next Step"**.
  - Show progress bar updating.
- [ ] **7. Demonstrate Auto-Advancement:**
  - Complete Network intent.
  - Show engine automatically switching focus to `[BLUETOOTH]` track without user click.
- [ ] **8. Demonstrate Final Resolution:**
  - Complete Bluetooth steps.
  - Celebrate with the **Resolution Card** showing all completed actions and resolved domains.

---

## 3. BACKUP SCENARIOS & RECOVERY PROCEDURES

| Failure Scenario | Fallback Action | Backup Query / Command |
|:---|:---|:---|
| **Query typo or network glitch** | Click pre-configured Quick Scenario button | Click `"Wi-Fi + Buds Disconnect"` card |
| **User prefers single issue** | Demonstrate atomic single-intent flow | `"My Wi-Fi keeps disconnecting"` |
| **Judge asks about error codes** | Demonstrate error-code intelligence | Enter `"ERR_WIFI_01"` or code `"1001"` |
| **Judge asks about screenshots** | Upload screenshot from test images | Select `test_images/realistic_screenshot.png` |
| **Judge asks about escalation** | Click "Didn't Work" repeatedly | Show automatic escalation to Samsung Support after 6 failures |

---

## 4. POST-DEMO AUDIT & TECHNICAL PROOF

Have these verification assets ready in separate browser tabs or terminal windows:

- [ ] **1. REST API Interactive Docs:**
  - `http://127.0.0.1:8000/docs` (FastAPI Swagger UI showing all 9 endpoints).
- [ ] **2. Architecture Documentation:**
  - [ARCHITECTURE.md](file:///c:/Users/anian/Downloads/participant-kit-all-themes/ARCHITECTURE.md)
- [ ] **3. Performance Benchmark Report:**
  - [PHASE_8_FINAL_VALIDATION.md](file:///c:/Users/anian/Downloads/participant-kit-all-themes/PHASE_8_FINAL_VALIDATION.md) (Highlighting 3.9ms cache, 43ms multi-intent).
- [ ] **4. Security & Guardrail Audit:**
  - [PHASE_8_STEP4_SECURITY_EDGE_CASE_AUDIT.md](file:///c:/Users/anian/Downloads/participant-kit-all-themes/PHASE_8_STEP4_SECURITY_EDGE_CASE_AUDIT.md) (Highlighting 49/49 tests passed, 0 URL leaks).
