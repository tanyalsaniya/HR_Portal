// ============================================================
//  static/js/features/alerts.js
//  Centralized Alert & Notification System — HR Portal v5.0
//  Provides: showToast, showConfirm, showDangerConfirm,
//            showPromptDialog, showAlert (info/warning/error)
// ============================================================

(function () {
    'use strict';

    // ─── Inject alert styles ───────────────────────────────────────────────
    const ALERT_STYLE_ID = 'hr-alert-system-styles';
    if (!document.getElementById(ALERT_STYLE_ID)) {
        const style = document.createElement('style');
        style.id = ALERT_STYLE_ID;
        style.textContent = `
/* ================================================================
   HR PORTAL — CENTRALIZED ALERT SYSTEM STYLES
   Compatible with light/dark theme via CSS variables
   ================================================================ */

/* ── Toast Container ─────────────────────────────────────────── */
#hrAlertToastContainer {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 99000;
    display: flex;
    flex-direction: column-reverse;
    gap: 10px;
    pointer-events: none;
}

/* ── Individual Toast ────────────────────────────────────────── */
.hr-toast {
    pointer-events: all;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background: var(--bg-card, #ffffff);
    border-radius: 14px;
    padding: 14px 16px 14px 16px;
    min-width: 300px;
    max-width: 400px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.13), 0 2px 8px rgba(0,0,0,0.07);
    border: 1px solid var(--border-color, #f1f3f7);
    border-left: 4px solid var(--toast-accent, #7c3aed);
    position: relative;
    overflow: hidden;
    transform: translateX(110%);
    opacity: 0;
    transition: transform 0.42s cubic-bezier(0.34, 1.56, 0.64, 1),
                opacity 0.3s ease;
    will-change: transform, opacity;
}

.hr-toast.hr-toast--show {
    transform: translateX(0);
    opacity: 1;
}

.hr-toast.hr-toast--hide {
    transform: translateX(110%);
    opacity: 0;
    transition: transform 0.3s cubic-bezier(0.4, 0, 1, 1),
                opacity 0.25s ease;
}

/* Icon wrapper */
.hr-toast__icon {
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--toast-icon-bg, rgba(124,58,237,0.1));
}

.hr-toast__icon svg {
    display: block;
}

/* Content */
.hr-toast__body {
    flex: 1;
    min-width: 0;
}

.hr-toast__title {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.8125rem;
    font-weight: 700;
    color: var(--text-main, #1e293b);
    line-height: 1.3;
    margin-bottom: 2px;
}

.hr-toast__message {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.775rem;
    font-weight: 400;
    color: var(--text-secondary, #475569);
    line-height: 1.45;
    word-break: break-word;
}

/* Close */
.hr-toast__close {
    flex-shrink: 0;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-light, #94a3b8);
    padding: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    transition: color 0.15s, background 0.15s;
    align-self: flex-start;
    margin-top: -1px;
}

.hr-toast__close:hover {
    color: var(--text-main, #1e293b);
    background: var(--bg-main, #f8fafc);
}

/* Progress bar */
.hr-toast__progress {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 3px;
    width: 100%;
    background: var(--toast-accent, #7c3aed);
    opacity: 0.35;
    transform-origin: left;
    transition: transform linear;
    border-radius: 0 0 14px 14px;
}

/* Type variants */
.hr-toast--success { --toast-accent: #10b981; --toast-icon-bg: rgba(16,185,129,0.1); }
.hr-toast--error   { --toast-accent: #ef4444; --toast-icon-bg: rgba(239,68,68,0.1); }
.hr-toast--warning { --toast-accent: #f59e0b; --toast-icon-bg: rgba(245,158,11,0.1); }
.hr-toast--info    { --toast-accent: #3b82f6; --toast-icon-bg: rgba(59,130,246,0.1); }

/* ── Modal Overlay ───────────────────────────────────────────── */
.hr-modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(7px);
    -webkit-backdrop-filter: blur(7px);
    z-index: 99500;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    opacity: 0;
    transition: opacity 0.25s ease;
    pointer-events: none;
}

.hr-modal-overlay.hr-modal--visible {
    opacity: 1;
    pointer-events: all;
}

/* ── Modal Card ──────────────────────────────────────────────── */
.hr-modal-card {
    background: var(--bg-card, #ffffff);
    border: 1px solid var(--border-color, #f1f3f7);
    border-radius: 22px;
    padding: 2.25rem 2.25rem 1.75rem;
    width: 420px;
    max-width: 93vw;
    box-shadow: 0 30px 80px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08);
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 0;
    transform: scale(0.82) translateY(20px);
    opacity: 0;
    transition: transform 0.38s cubic-bezier(0.34, 1.56, 0.64, 1),
                opacity 0.25s ease;
    will-change: transform, opacity;
    position: relative;
    overflow: hidden;
}

.hr-modal-overlay.hr-modal--visible .hr-modal-card {
    transform: scale(1) translateY(0);
    opacity: 1;
}

/* Gradient shimmer accent at the top */
.hr-modal-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--modal-accent-gradient, linear-gradient(90deg, #7c3aed, #a78bfa, #c084fc));
    border-radius: 22px 22px 0 0;
}

/* ── Modal Icon Ring ─────────────────────────────────────────── */
.hr-modal-icon-ring {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1.25rem;
    background: var(--modal-icon-bg, rgba(124,58,237,0.1));
    border: 2.5px solid var(--modal-icon-border, rgba(124,58,237,0.2));
    position: relative;
}

/* Pulse ring animation */
.hr-modal-icon-ring::after {
    content: '';
    position: absolute;
    inset: -6px;
    border-radius: 50%;
    border: 2px solid var(--modal-icon-border, rgba(124,58,237,0.15));
    animation: hr-ring-pulse 2.2s ease-in-out infinite;
}

@keyframes hr-ring-pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.1); opacity: 0.4; }
}

/* Type variants for icon ring */
.hr-modal--success .hr-modal-icon-ring { --modal-icon-bg: rgba(16,185,129,0.1); --modal-icon-border: rgba(16,185,129,0.25); }
.hr-modal--error   .hr-modal-icon-ring { --modal-icon-bg: rgba(239,68,68,0.1); --modal-icon-border: rgba(239,68,68,0.25); }
.hr-modal--warning .hr-modal-icon-ring { --modal-icon-bg: rgba(245,158,11,0.1); --modal-icon-border: rgba(245,158,11,0.25); }
.hr-modal--info    .hr-modal-icon-ring { --modal-icon-bg: rgba(59,130,246,0.1); --modal-icon-border: rgba(59,130,246,0.25); }
.hr-modal--danger  .hr-modal-icon-ring { --modal-icon-bg: rgba(239,68,68,0.1); --modal-icon-border: rgba(239,68,68,0.25); }

/* Gradient variants for top bar */
.hr-modal--success .hr-modal-card::before { background: linear-gradient(90deg, #10b981, #6ee7b7); }
.hr-modal--error   .hr-modal-card::before { background: linear-gradient(90deg, #ef4444, #fca5a5); }
.hr-modal--warning .hr-modal-card::before { background: linear-gradient(90deg, #f59e0b, #fcd34d); }
.hr-modal--info    .hr-modal-card::before { background: linear-gradient(90deg, #3b82f6, #93c5fd); }
.hr-modal--danger  .hr-modal-card::before { background: linear-gradient(90deg, #ef4444, #b91c1c); }

/* ── Modal Text ──────────────────────────────────────────────── */
.hr-modal-title {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 1.15rem;
    font-weight: 800;
    color: var(--text-main, #1e293b);
    margin-bottom: 0.5rem;
    line-height: 1.3;
    letter-spacing: -0.02em;
}

.hr-modal-body {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.875rem;
    color: var(--text-secondary, #475569);
    line-height: 1.6;
    margin-bottom: 1.5rem;
    max-width: 340px;
}

/* ── Modal Input (for prompt dialogs) ───────────────────────── */
.hr-modal-input-label {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.775rem;
    font-weight: 600;
    color: var(--text-secondary, #475569);
    text-align: left;
    width: 100%;
    margin-bottom: 6px;
}

.hr-modal-input {
    width: 100%;
    padding: 0.625rem 0.875rem;
    border: 1.5px solid var(--border-accent, #e2e8f0);
    border-radius: 10px;
    background: var(--bg-main, #f8fafc);
    color: var(--text-main, #1e293b);
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.18s, box-shadow 0.18s;
    box-sizing: border-box;
    margin-bottom: 0.5rem;
    resize: none;
}

.hr-modal-input:focus {
    border-color: #7c3aed;
    box-shadow: 0 0 0 3.5px rgba(124, 58, 237, 0.12);
}

.hr-modal-input-error {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.75rem;
    color: #ef4444;
    text-align: left;
    width: 100%;
    min-height: 18px;
    margin-bottom: 0.75rem;
}

.hr-modal-input-wrapper {
    width: 100%;
    text-align: left;
    margin-bottom: 1rem;
}

/* ── Modal Buttons ───────────────────────────────────────────── */
.hr-modal-actions {
    display: flex;
    gap: 10px;
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
}

.hr-modal-btn {
    padding: 0.625rem 1.5rem;
    border-radius: 9999px;
    border: none;
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.875rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    display: inline-flex;
    align-items: center;
    gap: 7px;
    letter-spacing: -0.01em;
    min-width: 110px;
    justify-content: center;
}

.hr-modal-btn--primary {
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    color: #fff;
    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);
}

.hr-modal-btn--primary:hover {
    background: linear-gradient(135deg, #6d28d9, #5b21b6);
    box-shadow: 0 6px 20px rgba(124, 58, 237, 0.45);
    transform: translateY(-1px);
}

.hr-modal-btn--primary:active { transform: translateY(0); }

.hr-modal-btn--danger {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    color: #fff;
    box-shadow: 0 4px 14px rgba(239, 68, 68, 0.35);
}

.hr-modal-btn--danger:hover {
    background: linear-gradient(135deg, #dc2626, #b91c1c);
    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.45);
    transform: translateY(-1px);
}

.hr-modal-btn--danger:active { transform: translateY(0); }

.hr-modal-btn--success {
    background: linear-gradient(135deg, #10b981, #059669);
    color: #fff;
    box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
}

.hr-modal-btn--success:hover {
    background: linear-gradient(135deg, #059669, #047857);
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45);
    transform: translateY(-1px);
}

.hr-modal-btn--cancel {
    background: var(--bg-main, #f8fafc);
    color: var(--text-secondary, #475569);
    border: 1.5px solid var(--border-accent, #e2e8f0);
    box-shadow: none;
}

.hr-modal-btn--cancel:hover {
    background: var(--border-color, #f1f3f7);
    color: var(--text-main, #1e293b);
    transform: translateY(-1px);
}

.hr-modal-btn--cancel:active { transform: translateY(0); }

/* ── Shake animation for validation errors ───────────────────── */
@keyframes hr-shake {
    0%, 100% { transform: translateX(0); }
    20% { transform: translateX(-6px); }
    40% { transform: translateX(6px); }
    60% { transform: translateX(-4px); }
    80% { transform: translateX(4px); }
}

.hr-modal-card--shake {
    animation: hr-shake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97);
}

/* ── Dark Mode overrides ─────────────────────────────────────── */
[data-theme="dark"] .hr-toast {
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3);
}

[data-theme="dark"] .hr-modal-overlay {
    background: rgba(0, 0, 0, 0.7);
}

[data-theme="dark"] .hr-modal-card {
    box-shadow: 0 30px 80px rgba(0,0,0,0.6), 0 4px 16px rgba(0,0,0,0.4);
}

[data-theme="dark"] .hr-modal-input {
    background: var(--bg-card, #111827);
    border-color: var(--border-accent, #374151);
}

[data-theme="dark"] .hr-modal-btn--cancel {
    background: var(--bg-sidebar, #111827);
    border-color: var(--border-accent, #374151);
}

/* ── Responsive ──────────────────────────────────────────────── */
@media (max-width: 480px) {
    #hrAlertToastContainer {
        left: 1rem;
        right: 1rem;
        bottom: 1rem;
    }
    .hr-toast { min-width: 0; max-width: 100%; }
    .hr-modal-card { padding: 1.75rem 1.5rem 1.5rem; border-radius: 18px; }
    .hr-modal-actions { flex-direction: column; }
    .hr-modal-btn { width: 100%; }
}
        `;
        document.head.appendChild(style);
    }

    // ─── Create/get Toast Container ────────────────────────────────────────
    function getToastContainer() {
        let el = document.getElementById('hrAlertToastContainer');
        if (!el) {
            el = document.createElement('div');
            el.id = 'hrAlertToastContainer';
            document.body.appendChild(el);
        }
        return el;
    }

    // ─── SVG Icon Registry ─────────────────────────────────────────────────
    const ICONS = {
        success: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`,
        error: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
        warning: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        info: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
        danger: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
        question: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        modalSuccess: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`,
        modalError: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
        modalWarning: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        modalInfo: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
        modalDanger: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
        modalQuestion: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        closeX: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
        send: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`,
        trashIcon: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
        checkIcon: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M20 6L9 17l-5-5"/></svg>`,
    };

    // ─── TYPE DISPLAY META ─────────────────────────────────────────────────
    const TYPE_META = {
        success: { label: 'Success',     toastIcon: ICONS.success, modalIcon: ICONS.modalSuccess },
        error:   { label: 'Error',       toastIcon: ICONS.error,   modalIcon: ICONS.modalError   },
        warning: { label: 'Warning',     toastIcon: ICONS.warning, modalIcon: ICONS.modalWarning },
        info:    { label: 'Information', toastIcon: ICONS.info,    modalIcon: ICONS.modalInfo    },
        danger:  { label: 'Attention',   toastIcon: ICONS.error,   modalIcon: ICONS.modalDanger  },
        confirm: { label: 'Confirm',     toastIcon: ICONS.info,    modalIcon: ICONS.modalQuestion },
    };

    // =====================================================================
    //  TOAST SYSTEM
    // =====================================================================

    /**
     * showToast(message, type, duration)
     * type: 'success' | 'error' | 'warning' | 'info'
     * duration: ms (default 4000)
     *
     * Replaces the old showToast in app.js — fully backwards compatible.
     */
    window.showToast = function (message, type = 'success', duration = 4000) {
        // Suppress success/info toasts if a SweetAlert/Success Modal is currently open to prevent duplicate popups
        if ((type === 'success' || type === 'info') && document.getElementById('hrSuccessModalOverlay')) {
            return;
        }
        
        const container = getToastContainer();
        const meta = TYPE_META[type] || TYPE_META.success;
        const toastId = 'hr-toast-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6);

        const toast = document.createElement('div');
        toast.className = `hr-toast hr-toast--${type}`;
        toast.id = toastId;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        toast.innerHTML = `
            <div class="hr-toast__icon">${meta.toastIcon}</div>
            <div class="hr-toast__body">
                <div class="hr-toast__title">${meta.label}</div>
                <div class="hr-toast__message">${message}</div>
            </div>
            <button class="hr-toast__close" onclick="this.closest('.hr-toast') && window._hrAlertDismissToast(this.closest('.hr-toast'))" aria-label="Close">${ICONS.closeX}</button>
            <div class="hr-toast__progress" id="${toastId}-bar"></div>
        `;

        container.prepend(toast);

        // Animate in
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                toast.classList.add('hr-toast--show');
            });
        });

        // Progress bar animation
        const bar = document.getElementById(`${toastId}-bar`);
        if (bar) {
            bar.style.transition = `transform ${duration}ms linear`;
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    bar.style.transform = 'scaleX(0)';
                });
            });
        }

        // Auto-dismiss
        const timer = setTimeout(() => {
            window._hrAlertDismissToast(toast);
        }, duration);

        toast._hrTimer = timer;

        // Pause on hover
        toast.addEventListener('mouseenter', () => {
            clearTimeout(toast._hrTimer);
            if (bar) bar.style.animationPlayState = 'paused';
        });

        toast.addEventListener('mouseleave', () => {
            const remaining = 1200;
            toast._hrTimer = setTimeout(() => {
                window._hrAlertDismissToast(toast);
            }, remaining);
        });
    };

    window._hrAlertDismissToast = function (toast) {
        if (!toast || toast._hrDismissed) return;
        toast._hrDismissed = true;
        clearTimeout(toast._hrTimer);
        toast.classList.remove('hr-toast--show');
        toast.classList.add('hr-toast--hide');
        setTimeout(() => toast.remove(), 350);
    };

    // =====================================================================
    //  MODAL DIALOG SYSTEM
    // =====================================================================

    let _activeModal = null;
    let _resolveModal = null;

    /** Internal: close and remove current modal */
    function _closeModal(result) {
        if (!_activeModal) return;
        const overlay = _activeModal;
        _activeModal = null;

        overlay.classList.remove('hr-modal--visible');
        setTimeout(() => {
            overlay.remove();
        }, 280);

        document.removeEventListener('keydown', _modalKeyHandler);

        if (_resolveModal) {
            const resolve = _resolveModal;
            _resolveModal = null;
            resolve(result);
        }
    }

    function _modalKeyHandler(e) {
        if (e.key === 'Escape') {
            _closeModal(null);
        }
        if (e.key === 'Enter' && _activeModal) {
            const confirmBtn = _activeModal.querySelector('[data-hr-modal-confirm]');
            if (confirmBtn && document.activeElement !== _activeModal.querySelector('.hr-modal-input')) {
                confirmBtn.click();
            }
        }
    }

    /** Internal: build and show modal, returns Promise<result> */
    function _createModal(options) {
        return new Promise((resolve) => {
            // If a modal is already open, close it first
            if (_activeModal) _closeModal(null);

            _resolveModal = resolve;

            const {
                type = 'confirm',     // confirm | danger | info | success | warning | error
                icon,
                title,
                body,
                confirmText = 'Confirm',
                cancelText = 'Cancel',
                confirmClass = 'hr-modal-btn--primary',
                showCancel = true,
                inputConfig = null,   // null | { label, placeholder, type:'text'|'textarea', required, validate }
            } = options;

            // Determine icon
            const iconKey = icon
                || (type === 'danger' ? 'modalDanger'
                    : type === 'success' ? 'modalSuccess'
                    : type === 'error' ? 'modalError'
                    : type === 'warning' ? 'modalWarning'
                    : type === 'info' ? 'modalInfo'
                    : 'modalQuestion');

            const overlay = document.createElement('div');
            overlay.className = `hr-modal-overlay hr-modal--${type}`;
            overlay.setAttribute('role', 'dialog');
            overlay.setAttribute('aria-modal', 'true');
            overlay.setAttribute('aria-labelledby', 'hrModalTitle');

            // Click outside to cancel
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) _closeModal(null);
            });

            const inputHtml = inputConfig ? `
                <div class="hr-modal-input-wrapper">
                    <div class="hr-modal-input-label">${inputConfig.label || ''}</div>
                    ${inputConfig.type === 'textarea'
                        ? `<textarea id="hrModalInput" class="hr-modal-input" rows="4" placeholder="${inputConfig.placeholder || ''}"></textarea>`
                        : `<input id="hrModalInput" class="hr-modal-input" type="${inputConfig.inputType || 'text'}" placeholder="${inputConfig.placeholder || ''}">`
                    }
                    <div class="hr-modal-input-error" id="hrModalInputError"></div>
                </div>
            ` : '';

            const cancelBtnHtml = showCancel
                ? `<button class="hr-modal-btn hr-modal-btn--cancel" id="hrModalCancel">${cancelText}</button>`
                : '';

            overlay.innerHTML = `
                <div class="hr-modal-card">
                    <div class="hr-modal-icon-ring">${ICONS[iconKey] || ICONS.modalQuestion}</div>
                    <div class="hr-modal-title" id="hrModalTitle">${title || 'Are you sure?'}</div>
                    <div class="hr-modal-body">${body || ''}</div>
                    ${inputHtml}
                    <div class="hr-modal-actions">
                        ${cancelBtnHtml}
                        <button class="hr-modal-btn ${confirmClass}" id="hrModalConfirm" data-hr-modal-confirm>${confirmText}</button>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);
            _activeModal = overlay;

            // Show animation
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    overlay.classList.add('hr-modal--visible');
                });
            });

            // Button events
            const confirmBtn = overlay.querySelector('#hrModalConfirm');
            const cancelBtn = overlay.querySelector('#hrModalCancel');
            const inputEl = overlay.querySelector('#hrModalInput');
            const errorEl = overlay.querySelector('#hrModalInputError');
            const card = overlay.querySelector('.hr-modal-card');

            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => _closeModal(null));
            }

            confirmBtn.addEventListener('click', () => {
                if (inputConfig) {
                    const val = inputEl ? inputEl.value.trim() : '';
                    // Validation
                    if (inputConfig.required && !val) {
                        if (errorEl) errorEl.textContent = inputConfig.requiredMsg || 'This field is required.';
                        // Shake
                        card.classList.remove('hr-modal-card--shake');
                        void card.offsetWidth;
                        card.classList.add('hr-modal-card--shake');
                        if (inputEl) inputEl.focus();
                        return;
                    }
                    if (inputConfig.validate) {
                        const errMsg = inputConfig.validate(val);
                        if (errMsg) {
                            if (errorEl) errorEl.textContent = errMsg;
                            card.classList.remove('hr-modal-card--shake');
                            void card.offsetWidth;
                            card.classList.add('hr-modal-card--shake');
                            if (inputEl) inputEl.focus();
                            return;
                        }
                    }
                    _closeModal({ confirmed: true, value: val });
                } else {
                    _closeModal({ confirmed: true });
                }
            });

            // Focus
            setTimeout(() => {
                if (inputEl) inputEl.focus();
                else if (confirmBtn) confirmBtn.focus();
            }, 80);

            document.addEventListener('keydown', _modalKeyHandler);
        });
    }

    // =====================================================================
    //  PUBLIC API
    // =====================================================================

    /**
     * showConfirm({ title, body, confirmText, cancelText }) → Promise<{confirmed}>|null
     */
    window.showConfirm = function (options) {
        return _createModal({
            type: 'confirm',
            title: options.title || 'Are you sure?',
            body: options.body || '',
            confirmText: options.confirmText || 'Yes, Continue',
            cancelText: options.cancelText || 'Cancel',
            confirmClass: 'hr-modal-btn--primary',
            showCancel: true,
            icon: options.icon || 'modalQuestion',
        });
    };

    /**
     * showDangerConfirm({ title, body, confirmText, cancelText }) → Promise<{confirmed}>|null
     * Styled with red destructive buttons.
     */
    window.showDangerConfirm = function (options) {
        return _createModal({
            type: 'danger',
            title: options.title || 'Are you sure?',
            body: options.body || 'This action cannot be undone.',
            confirmText: options.confirmText || 'Yes, Delete',
            cancelText: options.cancelText || 'Cancel',
            confirmClass: 'hr-modal-btn--danger',
            showCancel: true,
            icon: options.icon || 'modalDanger',
        });
    };

    /**
     * showPromptDialog({ title, body, label, placeholder, type, required, validate, confirmText }) → Promise<{confirmed, value}>|null
     */
    window.showPromptDialog = function (options) {
        return _createModal({
            type: options.dialogType || 'confirm',
            title: options.title || 'Enter Details',
            body: options.body || '',
            confirmText: options.confirmText || 'Submit',
            cancelText: options.cancelText || 'Cancel',
            confirmClass: options.confirmClass || 'hr-modal-btn--primary',
            showCancel: true,
            icon: options.icon || 'modalQuestion',
            inputConfig: {
                label: options.label || '',
                placeholder: options.placeholder || '',
                type: options.type || 'text',
                inputType: options.inputType || 'text',
                required: options.required !== false,
                requiredMsg: options.requiredMsg || 'This field cannot be empty.',
                validate: options.validate || null,
            },
        });
    };

    /**
     * showAlert({ type, title, body, confirmText }) → Promise<{confirmed}>
     * Non-cancelable informational dialog.
     */
    window.showAlert = function (options) {
        return _createModal({
            type: options.type || 'info',
            title: options.title || 'Notice',
            body: options.body || '',
            confirmText: options.confirmText || 'Got it',
            confirmClass: options.type === 'error' || options.type === 'danger'
                ? 'hr-modal-btn--danger'
                : options.type === 'success'
                ? 'hr-modal-btn--success'
                : 'hr-modal-btn--primary',
            showCancel: false,
        });
    };

    // =====================================================================
    //  SUCCESS MODAL — Matches the "Payment Successful" clean card design
    //  from the image: white card, green checkmark ring, bold title,
    //  grey subtitle, full-width black CTA button
    // =====================================================================

    // Inject extra styles for the success card design
    const SUCCESS_STYLE_ID = 'hr-success-modal-styles';
    if (!document.getElementById(SUCCESS_STYLE_ID)) {
        const ss = document.createElement('style');
        ss.id = SUCCESS_STYLE_ID;
        ss.textContent = `
/* ── Success Card Modal (Image-matched design) ───────────────── */
.hr-success-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.48);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    z-index: 99600;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    opacity: 0;
    transition: opacity 0.22s ease;
    pointer-events: none;
}
.hr-success-overlay.hr-success--visible {
    opacity: 1;
    pointer-events: all;
}

.hr-success-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 2rem 2rem 1.75rem;
    width: 360px;
    max-width: 92vw;
    box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 2px 8px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    position: relative;
    transform: scale(0.86) translateY(18px);
    opacity: 0;
    transition: transform 0.38s cubic-bezier(0.34, 1.56, 0.64, 1),
                opacity 0.26s ease;
    will-change: transform, opacity;
}
[data-theme="dark"] .hr-success-card {
    background: var(--bg-card, #111827);
    box-shadow: 0 20px 60px rgba(0,0,0,0.55), 0 2px 8px rgba(0,0,0,0.4);
}
.hr-success-overlay.hr-success--visible .hr-success-card {
    transform: scale(1) translateY(0);
    opacity: 1;
}

/* Close button top-right */
.hr-success-close {
    position: absolute;
    top: 14px;
    right: 16px;
    background: none;
    border: none;
    cursor: pointer;
    color: #94a3b8;
    font-size: 1.2rem;
    line-height: 1;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    transition: background 0.15s, color 0.15s;
    padding: 0;
}
.hr-success-close:hover {
    background: #f1f5f9;
    color: #1e293b;
}
[data-theme="dark"] .hr-success-close:hover {
    background: #1f2937;
    color: #f9fafb;
}

/* Icon ring */
.hr-success-icon {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1.1rem;
    position: relative;
}
.hr-success-icon--success { background: rgba(16,185,129,0.1); border: 2px solid rgba(16,185,129,0.2); }
.hr-success-icon--error   { background: rgba(239,68,68,0.1);  border: 2px solid rgba(239,68,68,0.2); }
.hr-success-icon--warning { background: rgba(245,158,11,0.1); border: 2px solid rgba(245,158,11,0.2); }
.hr-success-icon--info    { background: rgba(59,130,246,0.1);  border: 2px solid rgba(59,130,246,0.2); }

/* Outer pulse ring — matches image double ring */
.hr-success-icon::after {
    content: '';
    position: absolute;
    inset: -7px;
    border-radius: 50%;
    border: 1.5px solid currentColor;
    opacity: 0.15;
    animation: hr-success-pulse 2.4s ease-in-out infinite;
}
.hr-success-icon--success { color: #10b981; }
.hr-success-icon--error   { color: #ef4444; }
.hr-success-icon--warning { color: #f59e0b; }
.hr-success-icon--info    { color: #3b82f6; }

@keyframes hr-success-pulse {
    0%, 100% { transform: scale(1); opacity: 0.15; }
    50% { transform: scale(1.14); opacity: 0.06; }
}

/* Title */
.hr-success-title {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--text-main, #1e293b);
    margin-bottom: 0.4rem;
    letter-spacing: -0.02em;
    line-height: 1.3;
}

/* Subtitle */
.hr-success-subtitle {
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.85rem;
    color: var(--text-secondary, #64748b);
    line-height: 1.55;
    margin-bottom: 1.5rem;
    max-width: 280px;
}

/* CTA Button — full-width black pill */
.hr-success-btn {
    width: 100%;
    padding: 0.75rem 1.5rem;
    border-radius: 10px;
    border: none;
    background: #0f172a;
    color: #ffffff;
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.9rem;
    font-weight: 700;
    cursor: pointer;
    letter-spacing: -0.01em;
    transition: background 0.18s, transform 0.15s, box-shadow 0.18s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.25);
}
.hr-success-btn:hover {
    background: #1e293b;
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.32);
}
.hr-success-btn:active { transform: translateY(0); }
[data-theme="dark"] .hr-success-btn {
    background: #f9fafb;
    color: #0f172a;
    box-shadow: 0 4px 14px rgba(0,0,0,0.4);
}
[data-theme="dark"] .hr-success-btn:hover {
    background: #e2e8f0;
}

/* Secondary action link */
.hr-success-link {
    display: block;
    margin-top: 0.85rem;
    font-family: var(--font-family, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-secondary, #64748b);
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
    transition: color 0.15s;
    text-decoration: none;
}
.hr-success-link:hover { color: var(--text-main, #1e293b); }

/* Responsive */
@media (max-width: 480px) {
    .hr-success-card { padding: 1.75rem 1.5rem 1.5rem; border-radius: 16px; }
}
        `;
        document.head.appendChild(ss);
    }

    /**
     * showSuccessModal({
     *   type: 'success'|'error'|'warning'|'info',  // default: 'success'
     *   title,          // bold headline
     *   subtitle,       // grey body text
     *   btnText,        // CTA button label (default: 'Done')
     *   btnAction,      // optional function called on CTA click
     *   linkText,       // optional secondary link label
     *   linkAction,     // optional function called on link click
     * })
     *
     * The clean "Payment Successful" card design from the image.
     * Replaces showToast for important document generation successes.
     */
    window.showSuccessModal = function (options = {}) {
        const {
            type = 'success',
            title = 'Success!',
            subtitle = '',
            btnText = 'Done',
            btnAction = null,
            linkText = null,
            linkAction = null,
        } = options;

        // Close any existing success modal
        const existing = document.getElementById('hrSuccessModalOverlay');
        if (existing) existing.remove();

        // Clear any currently visible toasts so they don't overlap with the new modal
        const toastContainer = document.getElementById('hrToastContainer');
        if (toastContainer) {
            toastContainer.innerHTML = '';
        }

        // Icon SVG per type
        const iconSvgs = {
            success: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`,
            error:   `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
            warning: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
            info:    `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
        };

        const overlay = document.createElement('div');
        overlay.className = 'hr-success-overlay';
        overlay.id = 'hrSuccessModalOverlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');

        const linkHtml = linkText
            ? `<button class="hr-success-link" id="hrSuccessLink">${linkText}</button>`
            : '';

        overlay.innerHTML = `
            <div class="hr-success-card" id="hrSuccessCard">
                <button class="hr-success-close" id="hrSuccessClose" aria-label="Close">&#x2715;</button>
                <div class="hr-success-icon hr-success-icon--${type}">${iconSvgs[type] || iconSvgs.success}</div>
                <div class="hr-success-title">${title}</div>
                <div class="hr-success-subtitle">${subtitle}</div>
                <button class="hr-success-btn" id="hrSuccessBtn">${btnText}</button>
                ${linkHtml}
            </div>
        `;

        document.body.appendChild(overlay);

        // Click outside to close
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) _closeSuccessModal(overlay);
        });

        // Close button
        overlay.querySelector('#hrSuccessClose').addEventListener('click', () => {
            _closeSuccessModal(overlay);
        });

        // CTA button
        overlay.querySelector('#hrSuccessBtn').addEventListener('click', () => {
            _closeSuccessModal(overlay);
            if (typeof btnAction === 'function') btnAction();
        });

        // Link button
        const linkEl = overlay.querySelector('#hrSuccessLink');
        if (linkEl && linkAction) {
            linkEl.addEventListener('click', () => {
                _closeSuccessModal(overlay);
                if (typeof linkAction === 'function') linkAction();
            });
        }

        // Keyboard: Esc to close, Enter to confirm
        const kbHandler = (e) => {
            if (e.key === 'Escape' || e.key === 'Enter') {
                document.removeEventListener('keydown', kbHandler);
                _closeSuccessModal(overlay);
                if (e.key === 'Enter' && typeof btnAction === 'function') btnAction();
            }
        };
        document.addEventListener('keydown', kbHandler);

        // Show animation
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                overlay.classList.add('hr-success--visible');
                const btn = overlay.querySelector('#hrSuccessBtn');
                if (btn) setTimeout(() => btn.focus(), 100);
            });
        });
    };

    function _closeSuccessModal(overlay) {
        if (!overlay || !overlay.parentNode) return;
        overlay.classList.remove('hr-success--visible');
        setTimeout(() => {
            if (overlay.parentNode) overlay.remove();
        }, 280);
    }

    // =====================================================================
    //  BACKWARDS COMPAT: keep old toast container working if it exists
    //  (layout.html has id="toastContainer" — we don't remove it, but
    //   we now route all new toasts through hrAlertToastContainer)
    // =====================================================================

    console.log('%c[HR Alerts] Centralized alert system v5.1 loaded ✓', 'color: #7c3aed; font-weight: 700;');

})();

