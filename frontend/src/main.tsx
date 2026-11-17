import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";
import { markMobileApp } from "./lib/platform";
import { openRemindersOnTap } from "./lib/reminders";
markMobileApp();
openRemindersOnTap();
createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
