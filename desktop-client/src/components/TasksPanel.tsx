import React, { useState } from 'react';
import { TaskItem } from '../types';
import { CheckCircle2, Clock, ListTodo } from 'lucide-react';

interface TasksPanelProps {
  tasks: TaskItem[];
  onAddTask?: (task: Omit<TaskItem, 'id' | 'createdAt'>) => void;
}

export const TasksPanel: React.FC<TasksPanelProps> = ({ tasks }) => {
  const [filter, setFilter] = useState<'ALL' | 'PENDING' | 'DONE'>('ALL');

  const filteredTasks = tasks.filter(t => {
    if (filter === 'ALL') return true;
    if (filter === 'PENDING') return t.status === 'PENDING' || t.status === 'IN_PROGRESS';
    return t.status === 'DONE';
  });

  return (
    <div
      className="hud-panel hud-corners"
      style={{
        width: '320px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 'var(--radius-md)',
        flexShrink: 0,
        overflow: 'hidden'
      }}
    >
      {/* 1. Header de Tareas */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--cyan-border)',
        backgroundColor: 'rgba(4, 14, 28, 0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ListTodo size={16} color="var(--cyan-neon)" />
          <span style={{
            fontFamily: 'var(--font-hud)',
            fontSize: '13px',
            color: 'var(--cyan-neon)',
            letterSpacing: '1.5px',
            fontWeight: 700
          }}>
            MISSIONS // TASKS
          </span>
        </div>

        <span style={{
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          padding: '2px 8px',
          borderRadius: '3px',
          backgroundColor: 'rgba(0, 242, 255, 0.1)',
          color: 'var(--cyan-neon)',
          border: '1px solid var(--cyan-border)'
        }}>
          {tasks.length} ACTIVAS
        </span>
      </div>

      {/* 2. Filtros de Tareas */}
      <div style={{
        display: 'flex',
        padding: '8px 12px',
        gap: '6px',
        borderBottom: '1px solid rgba(0, 242, 255, 0.15)',
        backgroundColor: 'rgba(2, 8, 18, 0.4)'
      }}>
        {(['ALL', 'PENDING', 'DONE'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              flex: 1,
              padding: '4px 6px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              border: `1px solid ${filter === f ? 'var(--cyan-neon)' : 'transparent'}`,
              backgroundColor: filter === f ? 'rgba(0, 242, 255, 0.15)' : 'transparent',
              color: filter === f ? '#fff' : 'var(--text-muted)',
              borderRadius: '2px',
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            {f === 'ALL' ? 'TODAS' : f === 'PENDING' ? 'PENDIENTES' : 'COMPLETADAS'}
          </button>
        ))}
      </div>

      {/* 3. Lista de Tarjetas de Tareas */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        {filteredTasks.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--text-muted)',
            textAlign: 'center',
            gap: '8px',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px'
          }}>
            <CheckCircle2 size={24} color="var(--cyan-border)" />
            <p>SIN MISIONES ACTIVAS</p>
            <p style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
              Las tareas asignadas al agente se acumularán automáticamente aquí.
            </p>
          </div>
        ) : (
          filteredTasks.map(task => {
            const isDone = task.status === 'DONE';
            const inProgress = task.status === 'IN_PROGRESS';

            return (
              <div
                key={task.id}
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(4, 16, 32, 0.7)',
                  border: `1px solid ${inProgress ? 'var(--cyan-neon)' : isDone ? 'rgba(0, 255, 194, 0.3)' : 'rgba(0, 242, 255, 0.2)'}`,
                  boxShadow: inProgress ? '0 0 10px rgba(0, 242, 255, 0.15)' : 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}
              >
                {/* Cabecera de la tarjeta */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--cyan-neon)',
                    textTransform: 'uppercase'
                  }}>
                    {task.category}
                  </span>

                  <span style={{
                    fontSize: '9px',
                    fontFamily: 'var(--font-mono)',
                    padding: '1px 5px',
                    borderRadius: '2px',
                    backgroundColor: isDone 
                      ? 'rgba(0, 255, 194, 0.15)' 
                      : inProgress 
                      ? 'rgba(0, 242, 255, 0.2)' 
                      : 'rgba(255, 183, 0, 0.15)',
                    color: isDone 
                      ? 'var(--teal-accent)' 
                      : inProgress 
                      ? 'var(--cyan-neon)' 
                      : 'var(--amber-accent)',
                    border: `1px solid ${isDone ? 'rgba(0, 255, 194, 0.4)' : inProgress ? 'rgba(0, 242, 255, 0.4)' : 'rgba(255, 183, 0, 0.4)'}`
                  }}>
                    {task.status}
                  </span>
                </div>

                {/* Título de la tarea */}
                <h4 style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  color: isDone ? 'var(--text-muted)' : 'var(--text-primary)',
                  textDecoration: isDone ? 'line-through' : 'none',
                  margin: 0
                }}>
                  {task.title}
                </h4>

                {/* Descripción */}
                {task.description && (
                  <p style={{
                    fontSize: '11px',
                    color: 'var(--text-secondary)',
                    margin: 0,
                    lineHeight: '1.4'
                  }}>
                    {task.description}
                  </p>
                )}

                {/* Timestamp footer */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '9.5px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-dim)',
                  marginTop: '2px'
                }}>
                  <Clock size={10} />
                  <span>{task.createdAt}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
