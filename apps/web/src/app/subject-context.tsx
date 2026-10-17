import { createContext, useContext, useMemo, type ReactNode } from 'react';
import {
  Link,
  NavLink,
  useLocation,
  useNavigate,
  matchPath,
  type NavLinkProps,
  type LinkProps,
} from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, fail } from '../lib/api/client';
import type { components } from '../lib/api/schema';
type Ref = components['schemas']['SubjectRef'];
type Option = { value: string; label: string; kind: Ref['kind']; id: string | null; role: string };
type Context = {
  subject: Ref;
  key: string;
  label: string;
  available: boolean;
  authenticated: boolean;
  pending: boolean;
  options: Option[];
  select: (value: string) => void;
  href: (path: string) => string;
};
const personal: Ref = { kind: 'person', id: null };
const fallback: Context = {
  subject: personal,
  key: 'person:',
  label: 'My personal profile',
  available: true,
  authenticated: false,
  pending: false,
  options: [],
  select: () => {},
  href: (path) => path,
};
const Context = createContext<Context>(fallback);
export function SubjectProvider({
  children,
  enabled,
  hi,
}: {
  children: ReactNode;
  enabled: boolean;
  hi: boolean;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const params = new URLSearchParams(location.search);
  const dependent = matchPath('/people/:personId/edit', location.pathname)?.params.personId;
  const rawKind = dependent ? 'person' : (params.get('kind') ?? 'person');
  const rawId = dependent ?? params.get('id') ?? null;
  const kind = (
    ['person', 'household', 'business'].includes(rawKind) ? rawKind : 'person'
  ) as Ref['kind'];
  const query = useQuery({
    queryKey: ['workspaces'],
    enabled,
    retry: false,
    staleTime: 0,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/workspaces');
      return data ?? fail(error);
    },
  });
  const self = query.data
    ?.flatMap((w) => w.members)
    .find((m) => m.self === true && m.access === 'authorized');
  const id = kind === 'person' && self?.id === rawId ? null : rawId;
  const subject: Ref = { kind, id };
  const key = `${rawKind}:${id ?? ''}`;
  const options = useMemo(() => {
    const map = new Map<string, Option>();
    map.set('person:', {
      value: 'person:',
      label: hi ? 'मेरा व्यक्तिगत प्रोफ़ाइल' : 'My personal profile',
      kind: 'person',
      id: null,
      role: 'owner',
    });
    if (!query.isError)
      for (const w of query.data ?? []) {
        map.set(`${w.kind}:${w.id}`, {
          value: `${w.kind}:${w.id}`,
          label: `${w.kind === 'household' ? (hi ? 'परिवार' : 'Household') : hi ? 'व्यवसाय' : 'Business'} · ${w.name}`,
          kind: w.kind as Ref['kind'],
          id: w.id,
          role: w.role,
        });
        for (const m of w.members)
          if (m.id && m.access === 'authorized' && m.self !== true)
            map.set(`person:${String(m.id)}`, {
              value: `person:${String(m.id)}`,
              label: `${m.managed ? (hi ? 'आश्रित' : 'Dependent') : hi ? 'व्यक्ति' : 'Person'} · ${String(m.name)}`,
              kind: 'person',
              id: String(m.id),
              role: 'guardian',
            });
      }
    return Array.from(map.values());
  }, [hi, query.data, query.isError]);
  const selected = options.find((o) => o.value === key);
  const href = (path: string) => {
    if (!path.startsWith('/') || path.startsWith('//')) return path;
    const target = new URL(path, 'https://local.invalid');
    const editingPerson = matchPath('/people/:personId/edit', target.pathname)?.params.personId;
    if (editingPerson) {
      target.searchParams.set('kind', 'person');
      target.searchParams.set('id', editingPerson);
    }
    if (!target.searchParams.has('kind')) {
      if (subject.kind !== 'person' || subject.id) {
        target.searchParams.set('kind', subject.kind);
        if (subject.id) target.searchParams.set('id', subject.id);
      }
    }
    if (params.has('mode') && !target.searchParams.has('mode')) {
      const nextKind = target.searchParams.get('kind') || 'person';
      target.searchParams.set(
        'mode',
        params.get('mode') === 'explore'
          ? 'explore'
          : nextKind === 'business'
            ? 'business'
            : nextKind === 'household'
              ? 'family'
              : target.searchParams.get('id')
                ? 'member'
                : 'me',
      );
    }
    if (params.get('development') === 'true' && !target.searchParams.has('development'))
      target.searchParams.set('development', 'true');
    return target.pathname + target.search + target.hash;
  };
  const select = (value: string) => {
    if (!options.some((o) => o.value === value)) return;
    const [k, identifier] = value.split(':');
    const next = new URLSearchParams(location.search);
    if (k === 'person' && !identifier) {
      next.delete('kind');
      next.delete('id');
    } else {
      next.set('kind', k);
      if (identifier) next.set('id', identifier);
      else next.delete('id');
    }
    if (next.get('mode') !== 'explore')
      next.set(
        'mode',
        k === 'person' ? (identifier ? 'member' : 'me') : k === 'household' ? 'family' : 'business',
      );
    // Editing a dependent cannot silently retarget another person's form.
    const pathname = dependent ? '/profile' : location.pathname;
    navigate({ pathname, search: next.toString() });
  };
  return (
    <Context.Provider
      value={{
        subject,
        key,
        label: selected?.label ?? (hi ? 'यह संदर्भ उपलब्ध नहीं है' : 'This context is unavailable'),
        available: !!selected,
        authenticated: enabled,
        pending: enabled && query.isPending,
        options,
        select,
        href,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useSubject() {
  return useContext(Context);
}
export function ContextLink({ to, ...props }: LinkProps) {
  const context = useSubject();
  return <Link to={typeof to === 'string' ? context.href(to) : to} {...props} />;
}

export function ContextNavLink({ to, ...props }: NavLinkProps) {
  const context = useSubject();
  return <NavLink to={typeof to === 'string' ? context.href(to) : to} {...props} />;
}
