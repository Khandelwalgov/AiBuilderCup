import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useId,
  useState,
  useRef,
  type ReactNode,
} from 'react';
import { useBlocker } from 'react-router-dom';
type Guard = { register: (key: string, dirty: boolean) => void; confirmLeave: () => boolean };
const Context = createContext<Guard>({ register: () => {}, confirmLeave: () => true });
export function DirtyFormsProvider({ children, hi }: { children: ReactNode; hi: boolean }) {
  const [forms, setForms] = useState<Record<string, boolean>>({});
  const dirty = Object.values(forms).some(Boolean);
  const formsRef = useRef(forms);
  const register = useCallback((key: string, value: boolean) => {
    if (formsRef.current[key] === value) return;
    formsRef.current = { ...formsRef.current, [key]: value };
    setForms(formsRef.current);
  }, []);
  const confirmLeave = useCallback(
    () =>
      !Object.values(formsRef.current).some(Boolean) ||
      window.confirm(
        hi ? 'सहेजे नहीं गए बदलाव छोड़कर आगे बढ़ें?' : 'Leave and discard your unsaved changes?',
      ),
    [hi],
  );
  const blocker = useBlocker(() => Object.values(formsRef.current).some(Boolean));
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
  return { ...guard, markSaved: () => register(id, false) };
}
export function useDiscardGuard() {
  return useContext(Context);
}
