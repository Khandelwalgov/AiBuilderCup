import { matchPath } from 'react-router-dom';
import {
  House,
  Compass,
  UserRound,
  UsersRound,
  BriefcaseBusiness,
  Layers3,
  ShieldCheck,
  Settings2,
} from 'lucide-react';
import type { strings } from '../i18n/strings';
type Copy = (typeof strings)['en'];
export const routeMetadata = [
  { id: 'home', path: '/', titleKey: 'dashboard', nav: 'home', access: 'adaptive', icon: House },
  {
    id: 'discover',
    path: '/discover',
    titleKey: 'discover',
    nav: 'discover',
    access: 'public',
    icon: Compass,
  },
  {
    id: 'detail',
    path: '/opportunities/:id',
    titleKey: 'detail',
    nav: 'discover',
    parent: 'discover',
    access: 'public',
  },
  {
    id: 'profile',
    path: '/profile',
    titleKey: 'profile',
    nav: 'profile',
    access: 'authenticated',
    icon: UserRound,
  },
  {
    id: 'dependent',
    path: '/people/:personId/edit',
    titleKey: 'profile',
    nav: 'family',
    parent: 'family',
    access: 'authenticated',
  },
  {
    id: 'family',
    path: '/family',
    titleKey: 'family',
    nav: 'family',
    access: 'authenticated',
    icon: UsersRound,
  },
  {
    id: 'businesses',
    path: '/businesses',
    titleKey: 'businesses',
    nav: 'businesses',
    access: 'authenticated',
    icon: BriefcaseBusiness,
  },
  {
    id: 'plan',
    path: '/plan',
    titleKey: 'workspaceNav',
    nav: 'plan',
    access: 'authenticated',
    icon: Layers3,
  },
  {
    id: 'admin',
    path: '/admin',
    titleKey: 'adminReview',
    nav: 'admin',
    access: 'admin',
    icon: ShieldCheck,
  },
  {
    id: 'candidate',
    path: '/admin/reviews/:candidateId',
    titleKey: 'adminReview',
    nav: 'admin',
    parent: 'admin',
    access: 'admin',
  },
  {
    id: 'settings',
    path: '/settings',
    titleKey: 'settings',
    nav: 'settings',
    access: 'adaptive',
    icon: Settings2,
  },
] as const;
export function metadataFor(pathname: string) {
  return routeMetadata.find((r) => matchPath({ path: r.path, end: true }, pathname));
}
export function routeTitle(
  meta: ReturnType<typeof metadataFor>,
  t: Copy,
  hi: boolean,
  authenticated: boolean,
) {
  if (!meta) return hi ? 'पृष्ठ नहीं मिला' : 'Page not found';
  if (meta.id === 'home' && !authenticated) return hi ? 'होम' : 'Home';
  if (meta.id === 'dependent') return hi ? 'आश्रित का प्रोफ़ाइल' : 'Dependent profile';
  if (meta.id === 'candidate') return hi ? 'उम्मीदवार की समीक्षा' : 'Candidate review';
  if (meta.id === 'plan') return hi ? 'अनलॉक योजना' : 'Unlock plan';
  return t[meta.titleKey];
}
