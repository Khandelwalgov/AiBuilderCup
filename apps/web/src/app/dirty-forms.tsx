import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useId,
  useState,
  type ReactNode,
} from 'react';
import { useBlocker } from 'react-router-dom';
type Guard = { register: (key: string, dirty: boolean) => void; confirmLeave: () => boolean };
const Context = createContext<Guard>({ register: () => {}, confirmLeave: () => true });
export function DirtyFormsProvider({ children, hi }: { children: ReactNode; hi: boolean }) {
  const [forms, setForms] = useState<Record<string, boolean>>({});
  const dirty = Object.values(forms).some(Boolean);
  const register = useCallback(
    (key: string, value: boolean) =>
      setForms((old) => (old[key] === value ? old : { ...old, [key]: value })),
    [],
  );
  const confirmLeave = useCallback(
    () =>
      !dirty ||
      window.confirm(
        hi ? 'सहेजे नहीं गए बदलाव छोड़कर आगे बढ़ें?' : 'Leave and discard your unsaved changes?',
      ),
    [dirty, hi],
  );
  const blocker = useBlocker(dirty);
  useEffect(() => {
    if (blocker.state === 'blocked') {
      if (confirmLeave()) blocker.proceed();
      else blocker.reset();
    }
  }, [blocker, confirmLeave]);
  useEffect(() => {
    const before = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', before);
    return () => window.removeEventListener('beforeunload', before);
  }, [dirty]);
  return <Context.Provider value={{ register, confirmLeave }}>{children}</Context.Provider>;
}
export function useDirtyForm(dirty: boolean) {
  const id = useId();
  const guard = useContext(Context);
  const { register } = guard;
  useEffect(() => {
    register(id, dirty);
    return () => register(id, false);
  }, [id, dirty, register]);
  return guard;
}
export function useDiscardGuard() {
  return useContext(Context);
}
