import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router';
import { useEffect, useState } from 'react';
import {
  Badge,
  Button,
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  useIsMobile,
} from '@databricks/appkit-ui/react';
import {
  BarChart3,
  Compass,
  FolderUp,
  Menu,
  MessageSquareText,
  Sparkles,
  UserCheck,
} from 'lucide-react';
import { HomePage } from './pages/home/HomePage';
import { AnalyticsPage } from './pages/analytics/AnalyticsPage';
import { GeniePage } from './pages/genie/GeniePage';
import { FilesPage } from './pages/files/FilesPage';

interface WhoAmIResponse {
  email: string | null;
  user: string | null;
  executionMode: 'obo' | 'sp';
  genieSpaceConfigured: boolean;
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm font-medium inline-flex items-center gap-1.5 transition-colors ${
    isActive
      ? 'bg-primary text-primary-foreground'
      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
  }`;

const mobileNavLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? 'bg-primary text-primary-foreground'
      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
  }`;

type NavLinkClassFn = (props: { isActive: boolean }) => string;

function NavLinks({
  className,
  linkClass,
  onClick,
}: {
  className?: string;
  linkClass: NavLinkClassFn;
  onClick?: () => void;
}) {
  return (
    <nav className={className} aria-label="Navegação principal">
      <NavLink to="/" end className={linkClass} onClick={onClick}>
        <Compass className="h-4 w-4" />
        Início &amp; Tutorial
      </NavLink>
      <NavLink to="/analytics" className={linkClass} onClick={onClick}>
        <BarChart3 className="h-4 w-4" />
        Painel Gold
      </NavLink>
      <NavLink to="/genie" className={linkClass} onClick={onClick}>
        <MessageSquareText className="h-4 w-4" />
        Genie AI
      </NavLink>
      <NavLink to="/files" className={linkClass} onClick={onClick}>
        <FolderUp className="h-4 w-4" />
        Upload &amp; Volume
      </NavLink>
    </nav>
  );
}

function Layout() {
  const isMobile = useIsMobile();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [me, setMe] = useState<WhoAmIResponse | null>(null);

  useEffect(() => {
    fetch('/api/whoami')
      .then((res) => (res.ok ? res.json() : null))
      .then((data: WhoAmIResponse | null) => {
        if (data) setMe(data);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b border-border bg-card sticky top-0 z-20 px-4 md:px-6 py-3 flex items-center gap-4">
        <NavLink to="/" end className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <h1 className="text-sm sm:text-base font-semibold text-foreground">
              Meeting &amp; Video Intelligence
            </h1>
            <p className="text-[11px] text-muted-foreground hidden sm:block">
              Databricks Lakehouse • AI Functions • Genie Space
            </p>
          </div>
        </NavLink>

        <NavLinks className="hidden md:flex gap-1 ml-2" linkClass={navLinkClass} />

        <div className="ml-auto flex items-center gap-2">
          <Badge variant="secondary" className="hidden lg:inline-flex items-center gap-1.5">
            <UserCheck className="h-3.5 w-3.5" />
            {me?.email ?? me?.user ?? 'Databricks SSO'}
          </Badge>

          <div className="md:hidden">
            <Sheet open={mobileNavOpen && isMobile} onOpenChange={setMobileNavOpen}>
              <Button variant="ghost" size="icon" onClick={() => setMobileNavOpen(true)}>
                <Menu className="h-5 w-5" />
                <span className="sr-only">Abrir navegação</span>
              </Button>
              <SheetContent side="left">
                <SheetHeader>
                  <SheetTitle>Navegação</SheetTitle>
                </SheetHeader>
                <div className="mt-4 space-y-4">
                  <NavLinks
                    className="flex flex-col gap-1"
                    linkClass={mobileNavLinkClass}
                    onClick={() => setMobileNavOpen(false)}
                  />
                  <Badge variant="secondary" className="inline-flex items-center gap-1.5">
                    <UserCheck className="h-3.5 w-3.5" />
                    {me?.email ?? me?.user ?? 'Databricks SSO'}
                  </Badge>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>

      <main className="flex-1 p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  );
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/analytics', element: <AnalyticsPage /> },
      { path: '/genie', element: <GeniePage /> },
      { path: '/files', element: <FilesPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
