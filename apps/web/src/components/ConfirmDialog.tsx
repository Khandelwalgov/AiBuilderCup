import { useEffect, useRef, type ReactNode } from 'react';
export function ConfirmDialog({
  title,
  children,
  confirm,
  cancel,
  onConfirm,
  onCancel,
  disabled = false,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  confirm: string;
  cancel: string;
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    dialog?.showModal();
    return () => {
      dialog?.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="confirm-dialog"
      aria-labelledby="confirmation-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onCancel();
      }}
    >
      <h2 id="confirmation-title">{title}</h2>
      <div className="confirmation-body">{children}</div>
      <div className="dialog-actions">
        <button className="button secondary" disabled={busy} onClick={onCancel}>
          {cancel}
        </button>
        <button className="button" disabled={disabled || busy} onClick={onConfirm}>
          {busy ? '…' : confirm}
        </button>
      </div>
    </dialog>
  );
}
