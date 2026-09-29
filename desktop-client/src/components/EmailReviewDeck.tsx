import React, { useState, useEffect } from 'react';
import { EmailItem, EmailDraftData } from '../types';
import {
  Mail,
  ShieldCheck,
  Send,
  Trash2,
  RefreshCw,
  User,
  Calendar,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  AlertCircle,
  GraduationCap,
  Bell,
  FileText,
  X,
  Paperclip,
  CheckCircle2,
  Loader2,
  CornerDownRight,
  SlidersHorizontal
} from 'lucide-react';

interface EmailReviewDeckProps {
  emails: EmailItem[];
  activeDraft?: EmailDraftData | null;
  onGenerateDraft: (email: EmailItem, instructions?: string) => void;
  onApproveAndSend: (
    draftId: string,
    account: string,
    recipient: string,
    subject: string,
    body: string,
    emailId: string
  ) => void;
  onDiscardDraft: (draftId: string, emailId: string) => void;
  onClose?: () => void;
}

interface DraftState {
  draftId: string;
  body: string;
  isGenerating: boolean;
  isSent: boolean;
}

export const EmailReviewDeck: React.FC<EmailReviewDeckProps> = ({
  emails,
  activeDraft,
  onGenerateDraft,
  onApproveAndSend,
  onDiscardDraft,
  onClose
}) => {
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [showOriginal, setShowOriginal] = useState<boolean>(true);
  const [draftsMap, setDraftsMap] = useState<Record<string, DraftState>>({});
  const [customInstructions, setCustomInstructions] = useState<Record<string, string>>({});
  const [showPromptInput, setShowPromptInput] = useState<boolean>(false);
  const [sendingEmailId, setSendingEmailId] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Clamp current index within safe bounds
  const safeIndex = Math.max(0, Math.min(currentIndex, emails.length - 1));
  const currentEmail: EmailItem | undefined = emails[safeIndex];

  // Synchronize incoming activeDraft with local drafts map
  useEffect(() => {
    if (activeDraft) {
      setDraftsMap(prev => ({
        ...prev,
        [activeDraft.original_message_id]: {
          draftId: activeDraft.draft_id,
          body: activeDraft.draft_body,
          isGenerating: false,
          isSent: false
        }
      }));

      // Navigate to matching email if present
      const matchIdx = emails.findIndex(e => e.id === activeDraft.original_message_id);
      if (matchIdx !== -1 && matchIdx !== currentIndex) {
        setCurrentIndex(matchIdx);
      }
    }
  }, [activeDraft, emails]);

  // Empty state when all emails have been reviewed or inbox is empty
  if (!currentEmail || emails.length === 0) {
    return (
      <div
        className="hud-panel hud-corners"
        style={{
          flex: 1,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          borderRadius: 'var(--radius-md)',
          padding: '30px',
          gap: '16px',
          backgroundColor: 'rgba(10, 14, 23, 0.85)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(0, 242, 255, 0.25)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(0, 242, 255, 0.05)',
          textAlign: 'center'
        }}
      >
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          backgroundColor: 'rgba(0, 255, 194, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid rgba(0, 255, 194, 0.3)',
          boxShadow: '0 0 25px rgba(0, 255, 194, 0.2)'
        }}>
          <CheckCircle2 size={32} color="#00ffc2" />
        </div>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#fff', letterSpacing: '0.05em' }}>
            BANDEJA DE ENTRADA AL DÍA
          </h2>
          <p style={{ fontSize: '13px', color: 'rgba(255, 255, 255, 0.6)', marginTop: '6px', maxWidth: '380px' }}>
            No hay correos pendientes de revisión en este momento o todos los correos han sido gestionados.
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              marginTop: '10px',
              padding: '10px 24px',
              backgroundColor: 'rgba(0, 242, 255, 0.15)',
              border: '1px solid rgba(0, 242, 255, 0.4)',
              borderRadius: '6px',
              color: '#00f2ff',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            Volver al Panel Principal
          </button>
        )}
      </div>
    );
  }

  // Active draft state for current email
  const currentDraftState: DraftState | undefined = draftsMap[currentEmail.id];
  const hasDraft = !!currentDraftState && !!currentDraftState.body;
  const isGenerating = currentDraftState?.isGenerating || false;
  const isSent = currentDraftState?.isSent || false;

  // Category badge configuration
  const getCategoryBadge = (category: string) => {
    switch (category) {
      case 'URGENT':
        return {
          label: 'CRÍTICO / URGENTE',
          color: '#ff4b4b',
          bg: 'rgba(255, 75, 75, 0.15)',
          border: 'rgba(255, 75, 75, 0.4)',
          icon: <AlertCircle size={14} color="#ff4b4b" />
        };
      case 'UNIVERSITY':
        return {
          label: 'UNIVERSIDAD / ACADÉMICO',
          color: '#00f2ff',
          bg: 'rgba(0, 242, 255, 0.15)',
          border: 'rgba(0, 242, 255, 0.4)',
          icon: <GraduationCap size={14} color="#00f2ff" />
        };
      case 'NOTIFICATION':
        return {
          label: 'NOTIFICACIÓN AUTOMÁTICA',
          color: '#ffb700',
          bg: 'rgba(255, 183, 0, 0.15)',
          border: 'rgba(255, 183, 0, 0.4)',
          icon: <Bell size={14} color="#ffb700" />
        };
      case 'SPAM':
        return {
          label: 'SPAM / NO DESEADO',
          color: '#f43f5e',
          bg: 'rgba(244, 63, 94, 0.15)',
          border: 'rgba(244, 63, 94, 0.4)',
          icon: <AlertCircle size={14} color="#f43f5e" />
        };
      default:
        return {
          label: 'NO IMPORTANTE / GENERAL',
          color: '#94a3b8',
          bg: 'rgba(148, 163, 184, 0.15)',
          border: 'rgba(148, 163, 184, 0.3)',
          icon: <FileText size={14} color="#94a3b8" />
        };
    }
  };

  const catConfig = getCategoryBadge(currentEmail.category);
  const isGmail = currentEmail.account?.toUpperCase() === 'GMAIL';
  const recipientTarget = currentEmail.reply_to_address || currentEmail.from_address;
  const currentInstruction = customInstructions[currentEmail.id] || '';

  // Pagination navigation
  const handlePrev = () => {
    if (safeIndex > 0) {
      setCurrentIndex(safeIndex - 1);
      setShowPromptInput(false);
      setSuccessBanner(null);
    }
  };

  const handleNext = () => {
    if (safeIndex < emails.length - 1) {
      setCurrentIndex(safeIndex + 1);
      setShowPromptInput(false);
      setSuccessBanner(null);
    }
  };

  // Trigger AI draft generation
  const handleGenerateClick = () => {
    setDraftsMap(prev => ({
      ...prev,
      [currentEmail.id]: {
        draftId: prev[currentEmail.id]?.draftId || `draft-${Date.now()}`,
        body: prev[currentEmail.id]?.body || '',
        isGenerating: true,
        isSent: false
      }
    }));
    onGenerateDraft(currentEmail, currentInstruction || undefined);
  };

  // Draft editing
  const handleBodyChange = (text: string) => {
    setDraftsMap(prev => ({
      ...prev,
      [currentEmail.id]: {
        draftId: prev[currentEmail.id]?.draftId || `draft-${Date.now()}`,
        body: text,
        isGenerating: false,
        isSent: false
      }
    }));
  };

  // Discard draft
  const handleDiscardClick = () => {
    const draftId = currentDraftState?.draftId || `draft-${currentEmail.id}`;
    setDraftsMap(prev => {
      const next = { ...prev };
      delete next[currentEmail.id];
      return next;
    });
    onDiscardDraft(draftId, currentEmail.id);
  };

  // Approve and dispatch
  const handleSendClick = async () => {
    if (!currentDraftState || !currentDraftState.body.trim()) return;

    setSendingEmailId(currentEmail.id);
    const draftId = currentDraftState.draftId || `draft-${Date.now()}`;
    const subjectReply = currentEmail.subject.toLowerCase().startsWith('re:')
      ? currentEmail.subject
      : `Re: ${currentEmail.subject}`;

    onApproveAndSend(
      draftId,
      currentEmail.account,
      recipientTarget,
      subjectReply,
      currentDraftState.body,
      currentEmail.id
    );

    setDraftsMap(prev => ({
      ...prev,
      [currentEmail.id]: {
        ...prev[currentEmail.id],
        isGenerating: false,
        isSent: true
      }
    }));
    setSendingEmailId(null);
    setSuccessBanner(`Correo enviado con éxito a ${currentEmail.from_name || recipientTarget}`);

    // Automatically transition to next message if available
    if (safeIndex < emails.length - 1) {
      setTimeout(() => {
        setCurrentIndex(prev => Math.min(prev + 1, emails.length - 1));
        setSuccessBanner(null);
      }, 1500);
    }
  };

  return (
    <div
      className="hud-panel hud-corners"
      style={{
        flex: 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        padding: '16px 20px',
        gap: '12px',
        backgroundColor: 'rgba(10, 14, 23, 0.88)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 242, 255, 0.25)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(0, 242, 255, 0.05)'
      }}
    >
      {/* 1. Header Deck */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '34px',
            height: '34px',
            borderRadius: '8px',
            backgroundColor: 'rgba(0, 242, 255, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid rgba(0, 242, 255, 0.3)'
          }}>
            <Mail size={18} color="var(--cyan-neon, #00f2ff)" />
          </div>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '0.05em', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              BANDEJA DE ENTRADA INTELIGENTE
              <span style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '4px',
                fontWeight: 600,
                backgroundColor: isGmail ? 'rgba(234, 67, 53, 0.15)' : 'rgba(0, 120, 212, 0.15)',
                color: isGmail ? '#ea4335' : '#0078d4',
                border: `1px solid ${isGmail ? 'rgba(234, 67, 53, 0.3)' : 'rgba(0, 120, 212, 0.3)'}`
              }}>
                {currentEmail.account}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.5)', marginTop: '2px' }}>
              Cuenta: <span style={{ color: '#fff' }}>{currentEmail.account_address || 'Cuenta Configurada'}</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '6px',
            backgroundColor: catConfig.bg,
            border: `1px solid ${catConfig.border}`,
            color: catConfig.color,
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.05em'
          }}>
            {catConfig.icon}
            {catConfig.label}
          </div>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'rgba(255, 255, 255, 0.5)',
                cursor: 'pointer',
                padding: '4px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Cerrar vista de correos"
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* 2. Pagination Navigation Carousel */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 12px',
        backgroundColor: 'rgba(255, 255, 255, 0.03)',
        borderRadius: '6px',
        border: '1px solid rgba(255, 255, 255, 0.06)'
      }}>
        <button
          onClick={handlePrev}
          disabled={safeIndex === 0}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '4px 10px',
            borderRadius: '4px',
            backgroundColor: safeIndex === 0 ? 'rgba(255, 255, 255, 0.02)' : 'rgba(0, 242, 255, 0.1)',
            border: `1px solid ${safeIndex === 0 ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 242, 255, 0.3)'}`,
            color: safeIndex === 0 ? 'rgba(255, 255, 255, 0.25)' : '#00f2ff',
            fontSize: '11px',
            fontWeight: 600,
            cursor: safeIndex === 0 ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <ChevronLeft size={14} />
          Anterior
        </button>

        {/* Indicator dots */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'rgba(255, 255, 255, 0.85)' }}>
            Correo {safeIndex + 1} de {emails.length}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '6px' }}>
            {emails.map((e, idx) => {
              const isItemSent = draftsMap[e.id]?.isSent;
              const hasItemDraft = !!draftsMap[e.id]?.body;
              return (
                <div
                  key={e.id || idx}
                  onClick={() => {
                    setCurrentIndex(idx);
                    setSuccessBanner(null);
                  }}
                  title={`Correo ${idx + 1}: ${e.subject}`}
                  style={{
                    width: idx === safeIndex ? '20px' : '8px',
                    height: '8px',
                    borderRadius: '4px',
                    backgroundColor: isItemSent
                      ? '#00ffc2'
                      : idx === safeIndex
                      ? 'var(--cyan-neon, #00f2ff)'
                      : hasItemDraft
                      ? 'rgba(255, 183, 0, 0.6)'
                      : 'rgba(255, 255, 255, 0.2)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: idx === safeIndex ? '0 0 8px rgba(0, 242, 255, 0.5)' : 'none'
                  }}
                />
              );
            })}
          </div>
        </div>

        <button
          onClick={handleNext}
          disabled={safeIndex === emails.length - 1}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '4px 10px',
            borderRadius: '4px',
            backgroundColor: safeIndex === emails.length - 1 ? 'rgba(255, 255, 255, 0.02)' : 'rgba(0, 242, 255, 0.1)',
            border: `1px solid ${safeIndex === emails.length - 1 ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 242, 255, 0.3)'}`,
            color: safeIndex === emails.length - 1 ? 'rgba(255, 255, 255, 0.25)' : '#00f2ff',
            fontSize: '11px',
            fontWeight: 600,
            cursor: safeIndex === emails.length - 1 ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          Siguiente
          <ChevronRight size={14} />
        </button>
      </div>

      {/* Dispatch Success Notification Banner */}
      {successBanner && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          backgroundColor: 'rgba(0, 255, 194, 0.12)',
          border: '1px solid rgba(0, 255, 194, 0.4)',
          borderRadius: '6px',
          color: '#00ffc2',
          fontSize: '12px',
          fontWeight: 600
        }}>
          <span>{successBanner}</span>
          {safeIndex < emails.length - 1 && (
            <button
              onClick={handleNext}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#00ffc2',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '11px',
                textDecoration: 'underline'
              }}
            >
              Pasar al siguiente &rarr;
            </button>
          )}
        </div>
      )}

      {/* 3. RFC-822 Recipient Verification Box */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        borderRadius: '6px',
        backgroundColor: 'rgba(0, 255, 194, 0.06)',
        border: '1px solid rgba(0, 255, 194, 0.25)',
        boxShadow: '0 0 12px rgba(0, 255, 194, 0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={18} color="#00ffc2" />
          <div>
            <div style={{ fontSize: '10px', fontWeight: 800, color: '#00ffc2', letterSpacing: '0.06em' }}>
              REMITENTE VERIFICADO (RFC-822)
            </div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#ffffff', marginTop: '1px' }}>
              De: <span style={{ color: '#00f2ff' }}>{currentEmail.from_name || recipientTarget}</span> &lt;{recipientTarget}&gt;
            </div>
          </div>
        </div>
        <div style={{ fontSize: '10px', color: 'rgba(0, 255, 194, 0.8)', fontWeight: 600 }}>
          Reply-To Directo
        </div>
      </div>

      {/* 4. Subject and Date Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        backgroundColor: 'rgba(255, 255, 255, 0.03)',
        borderRadius: '6px',
        fontSize: '12px',
        color: 'rgba(255, 255, 255, 0.85)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
          <span style={{ color: 'rgba(255, 255, 255, 0.45)', flexShrink: 0 }}>Asunto:</span>
          <strong style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {currentEmail.subject}
          </strong>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'rgba(255, 255, 255, 0.45)', fontSize: '11px', flexShrink: 0, marginLeft: '8px' }}>
          <Calendar size={12} />
          {currentEmail.received_at
            ? new Date(currentEmail.received_at).toLocaleString('es-ES', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              })
            : 'Hoy'}
        </div>
      </div>

      {/* 5. Original Message Content Viewer */}
      <div style={{
        borderRadius: '6px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        backgroundColor: 'rgba(0, 0, 0, 0.25)',
        overflow: 'hidden'
      }}>
        <div
          onClick={() => setShowOriginal(!showOriginal)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '7px 12px',
            cursor: 'pointer',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            fontSize: '11px',
            fontWeight: 600,
            color: 'rgba(255, 255, 255, 0.7)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <User size={13} color="var(--cyan-neon, #00f2ff)" />
            <span>Contenido del Correo Recibido</span>
            {currentEmail.has_attachments && (
              <span style={{
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                fontSize: '10px',
                color: '#ffb700',
                backgroundColor: 'rgba(255, 183, 0, 0.1)',
                padding: '1px 6px',
                borderRadius: '4px'
              }}>
                <Paperclip size={10} />
                Adjuntos ({currentEmail.attachment_names?.length || 1})
              </span>
            )}
          </div>
          {showOriginal ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>

        {showOriginal && (
          <div style={{
            padding: '10px 12px',
            fontSize: '12px',
            color: 'rgba(255, 255, 255, 0.75)',
            lineHeight: '1.5',
            maxHeight: '110px',
            overflowY: 'auto',
            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
            whiteSpace: 'pre-wrap',
            fontFamily: 'inherit'
          }}>
            {currentEmail.body_text || currentEmail.body_snippet || '(Sin contenido de texto)'}
          </div>
        )}
      </div>

      {/* 6. Response Workspace */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        minHeight: '180px',
        position: 'relative'
      }}>
        {isGenerating ? (
          /* Drafting In Progress */
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '8px',
            border: '1px dashed rgba(0, 242, 255, 0.3)',
            gap: '12px',
            padding: '20px'
          }}>
            <Loader2 size={28} color="var(--cyan-neon, #00f2ff)" className="spin-animation" style={{ animation: 'spin 1s linear infinite' }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>
                Jarvis está redactando la respuesta...
              </div>
              <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.5)', marginTop: '4px' }}>
                Analizando contexto del remitente y aplicando directivas de seguridad.
              </div>
            </div>
          </div>
        ) : hasDraft ? (
          /* Draft Ready & Editable */
          <>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'rgba(255, 255, 255, 0.5)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600, color: 'var(--cyan-neon, #00f2ff)' }}>
                <Sparkles size={13} />
                Borrador de Respuesta (Editable por ti antes de enviar)
              </span>
              <span>{currentDraftState.body.length} caracteres</span>
            </div>

            <textarea
              value={currentDraftState.body}
              onChange={(e) => handleBodyChange(e.target.value)}
              placeholder="Escribe o modifica la respuesta antes de enviarla..."
              disabled={isSent || sendingEmailId === currentEmail.id}
              style={{
                flex: 1,
                width: '100%',
                backgroundColor: 'rgba(0, 0, 0, 0.4)',
                border: isSent ? '1px solid rgba(0, 255, 194, 0.3)' : '1px solid rgba(0, 242, 255, 0.25)',
                borderRadius: '8px',
                padding: '12px',
                color: '#fff',
                fontSize: '13px',
                lineHeight: '1.6',
                resize: 'none',
                outline: 'none',
                fontFamily: 'inherit',
                boxShadow: 'inset 0 2px 8px rgba(0, 0, 0, 0.4)'
              }}
              onFocus={(e) => {
                if (!isSent) {
                  e.currentTarget.style.borderColor = 'var(--cyan-neon, #00f2ff)';
                  e.currentTarget.style.boxShadow = '0 0 12px rgba(0, 242, 255, 0.2), inset 0 2px 8px rgba(0, 0, 0, 0.4)';
                }
              }}
              onBlur={(e) => {
                if (!isSent) {
                  e.currentTarget.style.borderColor = 'rgba(0, 242, 255, 0.25)';
                  e.currentTarget.style.boxShadow = 'inset 0 2px 8px rgba(0, 0, 0, 0.4)';
                }
              }}
            />
          </>
        ) : (
          /* Empty Draft Prompt */
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
            borderRadius: '8px',
            border: '1px dashed rgba(255, 255, 255, 0.12)',
            gap: '12px',
            padding: '20px'
          }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '50%',
              backgroundColor: 'rgba(0, 242, 255, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(0, 242, 255, 0.25)'
            }}>
              <Sparkles size={20} color="var(--cyan-neon, #00f2ff)" />
            </div>

            <div style={{ textAlign: 'center', maxWidth: '380px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>
                ¿Deseas que Jarvis redacte una respuesta para este correo?
              </div>
              <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.5)', marginTop: '3px' }}>
                Podrás revisar, editar el texto libremente y enviarlo con un solo clic.
              </div>
            </div>

            {showPromptInput && (
              <div style={{ width: '100%', maxWidth: '420px', marginTop: '4px' }}>
                <input
                  type="text"
                  value={currentInstruction}
                  onChange={(e) => setCustomInstructions(prev => ({ ...prev, [currentEmail.id]: e.target.value }))}
                  placeholder="Instrucción adicional (ej: 'Aceptar reunión el jueves a las 10h')..."
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    border: '1px solid rgba(0, 242, 255, 0.3)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#fff',
                    fontSize: '12px',
                    outline: 'none'
                  }}
                />
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <button
                onClick={() => setShowPromptInput(!showPromptInput)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '8px 12px',
                  backgroundColor: showPromptInput ? 'rgba(0, 242, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '6px',
                  color: showPromptInput ? '#00f2ff' : 'rgba(255, 255, 255, 0.7)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
                title="Añadir directiva personalizada para la IA"
              >
                <SlidersHorizontal size={13} />
                {showPromptInput ? 'Ocultar Directiva' : 'Personalizar Pautas'}
              </button>

              <button
                onClick={handleGenerateClick}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 18px',
                  backgroundColor: 'var(--cyan-neon, #00f2ff)',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#0a0e17',
                  fontSize: '12px',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  cursor: 'pointer',
                  boxShadow: '0 0 16px rgba(0, 242, 255, 0.35)',
                  transition: 'all 0.2s ease'
                }}
              >
                <Sparkles size={14} />
                GENERAR RESPUESTA CON IA
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 7. Action Controls Footer */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: '8px',
        borderTop: '1px solid rgba(255, 255, 255, 0.08)'
      }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {hasDraft && !isSent && (
            <>
              <button
                onClick={handleGenerateClick}
                disabled={isGenerating}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: 'rgba(255, 255, 255, 0.8)',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: isGenerating ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <RefreshCw size={13} />
                Regenerar
              </button>

              <button
                onClick={handleDiscardClick}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  backgroundColor: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.25)',
                  borderRadius: '6px',
                  color: '#f43f5e',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <Trash2 size={13} />
                Descartar
              </button>
            </>
          )}

          {safeIndex < emails.length - 1 && (
            <button
              onClick={handleNext}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '6px',
                color: 'rgba(255, 255, 255, 0.75)',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              Pasar al siguiente correo
              <CornerDownRight size={13} />
            </button>
          )}
        </div>

        {hasDraft && !isSent && (
          <button
            onClick={handleSendClick}
            disabled={sendingEmailId === currentEmail.id || !currentDraftState?.body?.trim()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 20px',
              backgroundColor: 'var(--cyan-neon, #00f2ff)',
              border: 'none',
              borderRadius: '6px',
              color: '#0a0e17',
              fontSize: '13px',
              fontWeight: 700,
              letterSpacing: '0.04em',
              cursor: sendingEmailId === currentEmail.id ? 'not-allowed' : 'pointer',
              boxShadow: '0 0 20px rgba(0, 242, 255, 0.4)',
              transition: 'all 0.2s ease'
            }}
          >
            {sendingEmailId === currentEmail.id ? (
              <>
                <Loader2 size={15} className="spin-animation" style={{ animation: 'spin 1s linear infinite' }} />
                ENVIANDO...
              </>
            ) : (
              <>
                <Send size={15} />
                APROBAR Y ENVIAR
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default EmailReviewDeck;
