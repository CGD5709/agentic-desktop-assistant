import React, { useState, useEffect } from "react";
import { ScheduledTask, ScheduledTaskStatus } from "../types";
import {
  Clock,
  Play,
  Pause,
  Trash2,
  Plus,
  Bell,
  CheckCircle2,
  ListTodo,
  Cpu,
  Mail,
  Globe,
  Network,
} from "lucide-react";

interface TasksPanelProps {
  tasks: ScheduledTask[];
  onOpenCreateModal: () => void;
  onToggleTask: (taskId: string, enabled: boolean) => void;
  onDeleteTask: (taskId: string) => void;
  onRunTaskNow: (taskId: string) => void;
}

export const TasksPanel: React.FC<TasksPanelProps> = ({
  tasks,
  onOpenCreateModal,
  onToggleTask,
  onDeleteTask,
  onRunTaskNow,
}) => {
  const [filter, setFilter] = useState<"ALL" | "ACTIVE" | "PAUSED" | "COMPLETED">("ALL");
  const [, setTick] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setTick((t) => t + 1), 10000);
    return () => clearInterval(timer);
  }, []);

  const filteredTasks = tasks.filter((t) => {
    if (filter === "ALL") return true;
    if (filter === "ACTIVE") return t.status === "ACTIVE";
    if (filter === "PAUSED") return t.status === "PAUSED";
    if (filter === "COMPLETED")
      return t.status === "COMPLETED" || t.status === "EXPIRED";
    return true;
  });

  const getToolIcon = (toolName: string) => {
    switch (toolName) {
      case "consultar_correos_no_leidos":
        return <Mail size={14} className="text-muted" />;
      case "analizar_rendimiento_procesos":
      case "matar_proceso":
        return <Cpu size={14} className="text-muted" />;
      case "escanear_puerto":
        return <Network size={14} className="text-muted" />;
      case "abrir_sitio_web":
        return <Globe size={14} className="text-muted" />;
      default:
        return <Bell size={14} className="text-muted" />;
    }
  };

  const formatCountdown = (nextRunIso?: string | null, status?: ScheduledTaskStatus) => {
    if (status === "COMPLETED") return "Completada";
    if (status === "EXPIRED") return "Expirada";
    if (status === "PAUSED") return "Pausada";
    if (!nextRunIso) return "Sin fecha futura";

    const now = new Date();
    const target = new Date(nextRunIso);
    const diffMs = target.getTime() - now.getTime();

    if (diffMs <= 0) return "Ejecutando...";

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `en ${diffDays}d ${diffHours % 24}h`;
    if (diffHours > 0) return `en ${diffHours}h ${diffMins % 60}m`;
    if (diffMins > 0) return `en ${diffMins} min`;
    return `en ${Math.floor(diffMs / 1000)}s`;
  };


  return (
    <div
      className="hud-panel"
      style={{
        width: "360px",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      {/* 1. Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px",
          borderBottom: "1px solid var(--border-color)",
          backgroundColor: "var(--bg-surface-elevated)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <ListTodo size={18} className="text-muted" />
          <span className="title-primary">
            Tareas Programadas
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontSize: "12px",
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-input)",
              color: "var(--text-muted)",
              border: "1px solid var(--border-color)",
              fontWeight: 500,
            }}
          >
            {tasks.filter((t) => t.status === "ACTIVE").length} Activas
          </span>

          <button
            onClick={onOpenCreateModal}
            title="Programar nueva tarea"
            className="hud-btn hud-btn-primary"
            style={{ padding: "6px", minWidth: "auto" }}
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      {/* 2. Filter Tabs */}
      <div
        style={{
          display: "flex",
          padding: "8px 12px",
          gap: "8px",
          borderBottom: "1px solid var(--border-color)",
          backgroundColor: "var(--bg-input)",
        }}
      >
        {(["ALL", "ACTIVE", "PAUSED", "COMPLETED"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              flex: 1,
              padding: "6px 0",
              fontSize: "11px",
              fontWeight: 500,
              border: "none",
              backgroundColor: filter === f ? "var(--bg-surface-elevated)" : "transparent",
              color: filter === f ? "var(--text-primary)" : "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              transition: "all 0.15s",
              boxShadow: filter === f ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
            }}
          >
            {f === "ALL"
              ? "Todas"
              : f === "ACTIVE"
                ? "Activas"
                : f === "PAUSED"
                  ? "Pausadas"
                  : "Historial"}
          </button>
        ))}
      </div>

      {/* 3. Task List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {filteredTasks.length === 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-muted)",
              textAlign: "center",
              gap: "12px",
              padding: "20px",
            }}
          >
            <CheckCircle2 size={32} style={{ opacity: 0.5 }} />
            <p style={{ margin: 0, fontSize: "14px", fontWeight: 500 }}>
              Sin tareas programadas
            </p>
            <p style={{ fontSize: "13px", margin: 0 }}>
              Pide al asistente que programe una tarea recurrente o haz clic en '+'.
            </p>
          </div>
        ) : (
          filteredTasks.map((task) => {
            const isActive = task.status === "ACTIVE";
            const isPaused = task.status === "PAUSED";
            const isCompleted = task.status === "COMPLETED";
            
            const statusColor = isActive ? "var(--success-color)" : isPaused ? "var(--warning-color)" : isCompleted ? "var(--text-muted)" : "var(--danger-color)";

            return (
              <div
                key={task.id}
                style={{
                  padding: "14px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-color)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                {/* Top Row: Tool & Trigger Type */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {getToolIcon(task.tool_name)}
                    <span
                      style={{
                        fontSize: "12px",
                        color: "var(--text-secondary)",
                        maxWidth: "140px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={task.tool_name}
                    >
                      {task.tool_name}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span
                      style={{
                        fontSize: "10px",
                        padding: "2px 6px",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: "var(--bg-input)",
                        color: "var(--text-muted)",
                        border: "1px solid var(--border-color)",
                      }}
                    >
                      {task.trigger_type === "ONE_SHOT" ? "Puntual" : task.trigger_type === "CRON" ? "Cron" : "Intervalo"}
                    </span>

                    <span
                      style={{
                        fontSize: "10px",
                        padding: "2px 6px",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: `${statusColor}15`,
                        color: statusColor,
                        border: `1px solid ${statusColor}40`,
                        fontWeight: 500,
                      }}
                    >
                      {task.status}
                    </span>
                  </div>
                </div>

                {/* Task Title */}
                <h4
                  style={{
                    fontSize: "14px",
                    fontWeight: 500,
                    color: isCompleted ? "var(--text-muted)" : "var(--text-primary)",
                    margin: 0,
                    lineHeight: "1.4",
                  }}
                >
                  {task.name}
                </h4>

                {/* Description */}
                {task.description && (
                  <p
                    style={{
                      fontSize: "12px",
                      color: "var(--text-muted)",
                      margin: 0,
                      lineHeight: "1.4",
                    }}
                  >
                    {task.description}
                  </p>
                )}

                {/* Footer: Countdown & Controls */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginTop: "4px",
                    paddingTop: "12px",
                    borderTop: "1px solid var(--border-color)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12px",
                      color: isActive ? "var(--text-secondary)" : "var(--text-muted)",
                    }}
                  >
                    <Clock size={14} />
                    <span>
                      {formatCountdown(task.next_run_at, task.status)}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <button
                      type="button"
                      onClick={() => onRunTaskNow(task.id)}
                      title="Ejecutar ahora"
                      className="hud-btn"
                      style={{ padding: "4px 8px" }}
                    >
                      <Play size={12} />
                    </button>

                    {(isActive || isPaused) && (
                      <button
                        type="button"
                        onClick={() => onToggleTask(task.id, isPaused)}
                        title={isActive ? "Pausar tarea" : "Reanudar tarea"}
                        className="hud-btn"
                        style={{ padding: "4px 8px" }}
                      >
                        {isActive ? <Pause size={12} /> : <Play size={12} />}
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => onDeleteTask(task.id)}
                      title="Eliminar tarea"
                      className="hud-btn hud-btn-danger"
                      style={{ padding: "4px 8px" }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
