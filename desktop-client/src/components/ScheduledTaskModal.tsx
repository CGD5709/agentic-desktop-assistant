import React, { useState } from "react";
import { TaskCreatePayload, TaskTriggerType } from "../types";
import {
  X,
  Calendar,
  Clock,
  Repeat,
  Bell,
  Play,
  Cpu,
  Mail,
  Globe,
  Network,
  AlertTriangle,
} from "lucide-react";

interface ScheduledTaskModalProps {
  isOpen: boolean;
  availableTools: string[];
  onClose: () => void;
  onCreateTask: (task: TaskCreatePayload) => void;
}

const PRESET_TOOLS = [
  {
    id: "notificacion_proactiva",
    name: "Recordatorio / Aviso",
    icon: Bell,
    category: "ASISTENTE",
  },
  {
    id: "consultar_correos_no_leidos",
    name: "Consultar Correos (Gmail)",
    icon: Mail,
    category: "EMAIL",
  },
  {
    id: "analizar_rendimiento_procesos",
    name: "Analizar Sistema",
    icon: Cpu,
    category: "SISTEMA",
  },
  {
    id: "escanear_puerto",
    name: "Escanear Puertos",
    icon: Network,
    category: "RED",
  },
  {
    id: "abrir_sitio_web",
    name: "Abrir Sitio Web",
    icon: Globe,
    category: "SISTEMA OPERATIVO",
  },
];

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const MINUTES = Array.from({ length: 60 }, (_, i) =>
  String(i).padStart(2, "0")
);

const DAY_LABELS = [
  { day: 1, label: "L", name: "Lunes" },
  { day: 2, label: "M", name: "Martes" },
  { day: 3, label: "X", name: "Miércoles" },
  { day: 4, label: "J", name: "Jueves" },
  { day: 5, label: "V", name: "Viernes" },
  { day: 6, label: "S", name: "Sábado" },
  { day: 0, label: "D", name: "Domingo" },
];

export const ScheduledTaskModal: React.FC<ScheduledTaskModalProps> = ({
  isOpen,
  availableTools,
  onClose,
  onCreateTask,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedTool, setSelectedTool] = useState("notificacion_proactiva");
  const [triggerType, setTriggerType] = useState<TaskTriggerType>("ONE_SHOT");
  const [notifyVoice, setNotifyVoice] = useState(true);

  // Helper date functions
  const getLocalDateStr = (d: Date = new Date()) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const getLocalHourStr = (d: Date = new Date()) => {
    return String(d.getHours()).padStart(2, "0");
  };

  const getLocalMinuteStr = (d: Date = new Date()) => {
    return String(d.getMinutes()).padStart(2, "0");
  };

  const initialFuture = new Date(Date.now() + 30 * 60 * 1000);

  const [selectedDate, setSelectedDate] = useState(() =>
    getLocalDateStr(initialFuture)
  );
  const [selectedHour, setSelectedHour] = useState(() =>
    getLocalHourStr(initialFuture)
  );
  const [selectedMinute, setSelectedMinute] = useState(() =>
    getLocalMinuteStr(initialFuture)
  );

  const [cronHour, setCronHour] = useState("08");
  const [cronMinute, setCronMinute] = useState("30");
  const [cronDays, setCronDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [isAdvancedCron, setIsAdvancedCron] = useState(false);
  const [customCronExpr, setCustomCronExpr] = useState("0 8 * * 1-5");

  const [intervalMinutes, setIntervalMinutes] = useState(30);

  const [processLimit, setProcessLimit] = useState(5);
  const [targetUrl, setTargetUrl] = useState("");
  const [targetPort, setTargetPort] = useState(8080);

  if (!isOpen) return null;

  const handleDayToggle = (day: number) => {
    setCronDays((prev) =>
      prev.includes(day)
        ? prev.filter((d) => d !== day)
        : [...prev, day].sort()
    );
  };

  const handleQuickOffset = (minutes: number) => {
    const d = new Date(Date.now() + minutes * 60 * 1000);
    setSelectedDate(getLocalDateStr(d));
    setSelectedHour(getLocalHourStr(d));
    setSelectedMinute(getLocalMinuteStr(d));
  };

  const handleSetPresetDate = (daysFromNow: number) => {
    const d = new Date();
    d.setDate(d.getDate() + daysFromNow);
    setSelectedDate(getLocalDateStr(d));
  };

  const getTargetExecutionDate = () => {
    try {
      const parts = selectedDate.split("-");
      if (parts.length !== 3) return null;
      const y = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10) - 1;
      const d = parseInt(parts[2], 10);
      const h = parseInt(selectedHour, 10);
      const min = parseInt(selectedMinute, 10);
      return new Date(y, m, d, h, min, 0);
    } catch {
      return null;
    }
  };

  const targetDateObj =
    triggerType === "ONE_SHOT" ? getTargetExecutionDate() : null;
  const isTargetInPast = targetDateObj
    ? targetDateObj.getTime() <= Date.now()
    : false;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) return;

    let toolArgs: Record<string, any> = {};
    if (selectedTool === "consultar_correos_no_leidos") {
      toolArgs = { account: "GMAIL", cuenta: "GMAIL" };
    } else if (selectedTool === "analizar_rendimiento_procesos") {
      toolArgs = { limite: Number(processLimit) };
    } else if (selectedTool === "abrir_sitio_web") {
      toolArgs = { url: targetUrl };
    } else if (selectedTool === "escanear_puerto") {
      toolArgs = { puerto: Number(targetPort) };
    }

    let triggerConfig: Record<string, any> = {};

    if (triggerType === "ONE_SHOT") {
      const parts = selectedDate.split("-");
      if (parts.length === 3) {
        const y = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10) - 1;
        const d = parseInt(parts[2], 10);
        const h = parseInt(selectedHour, 10);
        const min = parseInt(selectedMinute, 10);
        const localDate = new Date(y, m, d, h, min, 0);
        triggerConfig = { run_at: localDate.toISOString() };
      } else {
        triggerConfig = { run_at: new Date().toISOString() };
      }
    } else if (triggerType === "CRON") {
      if (isAdvancedCron) {
        triggerConfig = { cron_expr: customCronExpr };
      } else {
        const h = parseInt(cronHour, 10);
        const m = parseInt(cronMinute, 10);
        const daysStr =
          cronDays.length === 7 || cronDays.length === 0
            ? "*"
            : cronDays.join(",");
        triggerConfig = { cron_expr: `${m} ${h} * * ${daysStr}` };
      }
    } else if (triggerType === "INTERVAL") {
      triggerConfig = { interval_seconds: intervalMinutes * 60 };
    }

    onCreateTask({
      name: name.trim(),
      description: description.trim(),
      tool_name: selectedTool,
      tool_arguments: toolArgs,
      trigger_type: triggerType,
      trigger_config: triggerConfig,
      notify_voice: notifyVoice,
    });

    onClose();
  };

  const todayMinStr = getLocalDateStr(new Date());

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.6)",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
    >
      <div
        className="hud-panel"
        style={{
          width: "100%",
          maxWidth: "580px",
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border-color)",
            backgroundColor: "var(--bg-surface-elevated)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Calendar size={18} className="text-muted" />
            <span className="title-primary">Programar Nueva Tarea</span>
          </div>
          <button
            onClick={onClose}
            className="hud-btn"
            style={{ padding: "6px", minWidth: "auto", border: "none", background: "transparent" }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form
          onSubmit={handleSubmit}
          style={{
            padding: "24px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "20px",
            backgroundColor: "var(--bg-surface)",
          }}
        >
          {/* Task Name */}
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "8px" }}>
              Nombre de la tarea *
            </label>
            <input
              type="text"
              required
              placeholder="Ej: Revisión matutina de correos"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{ width: "100%" }}
            />
          </div>

          {/* Trigger Type Selection */}
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "8px" }}>
              Frecuencia
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
              <button
                type="button"
                onClick={() => setTriggerType("ONE_SHOT")}
                className={`hud-btn ${triggerType === "ONE_SHOT" ? "active" : ""}`}
                style={{ padding: "10px", fontSize: "12px" }}
              >
                <Calendar size={14} />
                Una vez
              </button>
              <button
                type="button"
                onClick={() => setTriggerType("CRON")}
                className={`hud-btn ${triggerType === "CRON" ? "active" : ""}`}
                style={{ padding: "10px", fontSize: "12px" }}
              >
                <Repeat size={14} />
                Rutina
              </button>
              <button
                type="button"
                onClick={() => setTriggerType("INTERVAL")}
                className={`hud-btn ${triggerType === "INTERVAL" ? "active" : ""}`}
                style={{ padding: "10px", fontSize: "12px" }}
              >
                <Clock size={14} />
                Intervalo
              </button>
            </div>
          </div>

          {/* Trigger Details Config */}
          <div
            style={{
              padding: "16px",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-color)",
              borderRadius: "var(--radius-md)",
            }}
          >
            {/* ONE_SHOT */}
            {triggerType === "ONE_SHOT" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontSize: "12px", fontWeight: 500, color: "var(--text-primary)" }}>
                      Día de ejecución
                    </span>
                    <div style={{ display: "flex", gap: "6px" }}>
                      <button type="button" className="hud-btn" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => handleSetPresetDate(0)}>Hoy</button>
                      <button type="button" className="hud-btn" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => handleSetPresetDate(1)}>Mañana</button>
                    </div>
                  </div>
                  <input
                    type="date"
                    required
                    min={todayMinStr}
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    style={{ width: "100%" }}
                  />
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontSize: "12px", fontWeight: 500, color: "var(--text-primary)" }}>
                      Hora exacta
                    </span>
                    <div style={{ display: "flex", gap: "6px" }}>
                      <button type="button" className="hud-btn" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => handleQuickOffset(15)}>+15m</button>
                      <button type="button" className="hud-btn" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => handleQuickOffset(30)}>+30m</button>
                      <button type="button" className="hud-btn" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => handleQuickOffset(60)}>+1h</button>
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: "12px" }}>
                    <select
                      value={selectedHour}
                      onChange={(e) => setSelectedHour(e.target.value)}
                      style={{ width: "100%" }}
                    >
                      {HOURS.map((h) => <option key={h} value={h}>{h}</option>)}
                    </select>
                    <span style={{ fontWeight: 600 }}>:</span>
                    <select
                      value={selectedMinute}
                      onChange={(e) => setSelectedMinute(e.target.value)}
                      style={{ width: "100%" }}
                    >
                      {MINUTES.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                </div>

                {isTargetInPast && (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--danger-color)", fontSize: "12px", marginTop: "8px" }}>
                    <AlertTriangle size={14} />
                    <span>La hora seleccionada ya ha pasado.</span>
                  </div>
                )}
              </div>
            )}

            {/* CRON */}
            {triggerType === "CRON" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {!isAdvancedCron ? (
                  <>
                    <div>
                      <span style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-primary)", marginBottom: "8px" }}>
                        Hora de ejecución
                      </span>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: "12px" }}>
                        <select value={cronHour} onChange={(e) => setCronHour(e.target.value)} style={{ width: "100%" }}>
                          {HOURS.map((h) => <option key={h} value={h}>{h}</option>)}
                        </select>
                        <span style={{ fontWeight: 600 }}>:</span>
                        <select value={cronMinute} onChange={(e) => setCronMinute(e.target.value)} style={{ width: "100%" }}>
                          {MINUTES.map((m) => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </div>
                    </div>

                    <div>
                      <span style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-primary)", marginBottom: "8px" }}>
                        Días de la semana
                      </span>
                      <div style={{ display: "flex", gap: "8px" }}>
                        {DAY_LABELS.map(({ day, label }) => {
                          const isSelected = cronDays.includes(day);
                          return (
                            <button
                              key={day}
                              type="button"
                              onClick={() => handleDayToggle(day)}
                              className={`hud-btn ${isSelected ? "active" : ""}`}
                              style={{ flex: 1, padding: "8px 0" }}
                            >
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </>
                ) : (
                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-primary)", marginBottom: "8px" }}>
                      Expresión Cron
                    </label>
                    <input
                      type="text"
                      placeholder="0 8 * * 1-5"
                      value={customCronExpr}
                      onChange={(e) => setCustomCronExpr(e.target.value)}
                      style={{ width: "100%" }}
                    />
                  </div>
                )}
                <div style={{ textAlign: "right" }}>
                  <button
                    type="button"
                    onClick={() => setIsAdvancedCron(!isAdvancedCron)}
                    style={{ background: "none", border: "none", color: "var(--primary-accent)", fontSize: "11px", cursor: "pointer", textDecoration: "underline" }}
                  >
                    {isAdvancedCron ? "Volver a simple" : "Modo avanzado"}
                  </button>
                </div>
              </div>
            )}

            {/* INTERVAL */}
            {triggerType === "INTERVAL" && (
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-primary)", marginBottom: "8px" }}>
                  Repetir cada (minutos)
                </label>
                <input
                  type="number"
                  min={1}
                  value={intervalMinutes}
                  onChange={(e) => setIntervalMinutes(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  style={{ width: "100%" }}
                />
              </div>
            )}
          </div>

          {/* Tool Selection */}
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "8px" }}>
              Acción a ejecutar *
            </label>
            <select
              value={selectedTool}
              onChange={(e) => setSelectedTool(e.target.value)}
              style={{ width: "100%" }}
            >
              {PRESET_TOOLS.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
              {availableTools
                .filter((t) => !PRESET_TOOLS.some((pt) => pt.id === t))
                .map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
            </select>
          </div>

          {/* Tool Specific Configs */}
          {selectedTool === "analizar_rendimiento_procesos" && (
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "8px" }}>
                Límite de procesos
              </label>
              <input
                type="number"
                min={1}
                value={processLimit}
                onChange={(e) => setProcessLimit(parseInt(e.target.value, 10) || 5)}
                style={{ width: "100%" }}
              />
            </div>
          )}

          {selectedTool === "abrir_sitio_web" && (
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "8px" }}>
                URL a abrir
              </label>
              <input
                type="url"
                required
                placeholder="https://..."
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
          )}

          {selectedTool === "escanear_puerto" && (
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "8px" }}>
                Puerto
              </label>
              <input
                type="number"
                min={1}
                value={targetPort}
                onChange={(e) => setTargetPort(parseInt(e.target.value, 10) || 8080)}
                style={{ width: "100%" }}
              />
            </div>
          )}

          {/* Description */}
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "8px" }}>
              Descripción o Instrucción
            </label>
            <textarea
              rows={2}
              placeholder="Añade contexto adicional para la tarea..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                backgroundColor: "var(--bg-input)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text-primary)",
                resize: "none",
                fontFamily: "var(--font-sans)",
                fontSize: "13px",
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="checkbox"
              id="notify_voice_check"
              checked={notifyVoice}
              onChange={(e) => setNotifyVoice(e.target.checked)}
              style={{ cursor: "pointer", width: "16px", height: "16px" }}
            />
            <label htmlFor="notify_voice_check" style={{ fontSize: "13px", color: "var(--text-primary)", cursor: "pointer" }}>
              Notificar por voz al completar
            </label>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "10px", paddingTop: "20px", borderTop: "1px solid var(--border-color)" }}>
            <button type="button" onClick={onClose} className="hud-btn">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isTargetInPast}
              className="hud-btn hud-btn-primary"
              style={{ opacity: isTargetInPast ? 0.5 : 1, cursor: isTargetInPast ? "not-allowed" : "pointer" }}
            >
              <Play size={14} />
              Crear Tarea
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
