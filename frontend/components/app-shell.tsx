"use client";

import {
  ChartBarIcon,
  DatabaseIcon,
  GearSixIcon,
  GraphIcon,
  MagnifyingGlassIcon,
  PlugsIcon,
  type IconProps,
} from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<IconProps>;
}

const navigation: NavItem[] = [
  { href: "/sources", label: "Sources", icon: DatabaseIcon },
  { href: "/ask", label: "Ask", icon: MagnifyingGlassIcon },
  { href: "/dashboards", label: "Dashboards", icon: ChartBarIcon },
  { href: "/settings", label: "Settings", icon: GearSixIcon },
];

function isCurrent(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      href="/sources"
      className={cn(
        "inline-flex min-h-11 items-center gap-2 rounded-md font-semibold tracking-tight",
        compact ? "text-primary" : "text-on-primary",
      )}
      aria-label="InsightMesh home"
    >
      <span className="grid size-9 place-items-center rounded-md bg-accent text-on-accent">
        <GraphIcon size={21} weight="bold" aria-hidden />
      </span>
      <span className="text-lg">InsightMesh</span>
    </Link>
  );
}

function NavigationLink({
  item,
  pathname,
  mobile = false,
}: {
  item: NavItem;
  pathname: string;
  mobile?: boolean;
}) {
  const active = isCurrent(pathname, item.href);
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex min-h-11 items-center rounded-md text-sm font-medium transition-colors duration-200",
        mobile ? "min-w-16 flex-1 flex-col justify-center gap-0.5 px-1 py-1 text-xs" : "gap-3 px-3",
        active
          ? mobile
            ? "bg-muted text-primary"
            : "bg-sidebar-hover text-on-primary"
          : mobile
            ? "text-muted-foreground hover:bg-muted hover:text-text"
            : "text-sidebar-muted hover:bg-sidebar-hover hover:text-on-primary",
      )}
    >
      <Icon size={mobile ? 20 : 19} weight={active ? "bold" : "regular"} aria-hidden />
      <span>{item.label}</span>
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <a
        href="#main-content"
        className="fixed left-3 top-3 z-50 -translate-y-20 rounded-md bg-card px-4 py-2 font-semibold text-primary shadow-float transition-transform focus:translate-y-0"
      >
        Skip to main content
      </a>

      <aside className="sticky top-0 hidden h-dvh flex-col bg-sidebar px-4 py-5 lg:flex">
        <Brand />
        <nav className="mt-8 flex flex-col gap-1" aria-label="Primary navigation">
          {navigation.map((item) => (
            <NavigationLink key={item.href} item={item} pathname={pathname} />
          ))}
        </nav>
        <div className="mt-auto border-t border-white/15 pt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-sidebar-muted">Active source</p>
          <div className="mt-2 flex items-center gap-2 text-sm text-on-primary">
            <PlugsIcon size={18} aria-hidden />
            <span>No source selected</span>
          </div>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex min-h-16 items-center justify-between gap-3 border-b border-border bg-card/95 px-4 backdrop-blur-sm sm:px-6 lg:justify-end">
          <div className="lg:hidden">
            <Brand compact />
          </div>
          <Link
            href="/sources"
            className="flex min-h-11 min-w-0 items-center gap-2 rounded-md border border-border bg-background px-3 text-sm text-muted-foreground transition-colors duration-200 hover:border-border-strong hover:text-text"
          >
            <PlugsIcon className="shrink-0" size={18} aria-hidden />
            <span className="hidden sm:inline">Active source:</span>
            <strong className="truncate font-semibold text-text">None</strong>
          </Link>
        </header>

        <main
          id="main-content"
          tabIndex={-1}
          className="mx-auto min-h-[calc(100dvh-4rem)] w-full max-w-[100rem] px-4 py-5 pb-24 sm:px-6 sm:py-6 lg:px-8 lg:py-7 lg:pb-8"
        >
          {children}
        </main>
      </div>

      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex min-h-16 items-stretch gap-1 border-t border-border bg-card/98 px-2 pb-[env(safe-area-inset-bottom)] pt-1 shadow-float lg:hidden"
        aria-label="Primary navigation"
      >
        {navigation.map((item) => (
          <NavigationLink key={item.href} item={item} pathname={pathname} mobile />
        ))}
      </nav>
    </div>
  );
}
