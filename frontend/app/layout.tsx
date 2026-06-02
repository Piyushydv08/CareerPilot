import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ProjectProvider } from "./context/ProjectContext";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CareerPilot - Premium AI Career Intelligence Platform",
  description: "High-contrast cyber blue predictive career intelligence, resume scanners, skill gap simulations, and real-time AI interview mocks.",
  keywords: "career pilot, AI career, resume optimization, interview simulator, skill gap analysis",
  authors: [{ name: "Antigravity Team" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans bg-bg-deep text-on-surface antialiased min-h-screen flex`}>
        <ProjectProvider>
          {/* Static Sidebar */}
          <Sidebar />

          {/* Main Layout Container */}
          <div className="flex-1 ml-64 flex flex-col min-h-screen bg-[#030305] relative overflow-hidden">
            {/* Pulsing visual glow backgrounds */}
            <div className="absolute top-0 right-1/4 h-[300px] w-[500px] bg-cyber-blue/5 blur-[120px] rounded-full pointer-events-none z-0"></div>
            <div className="absolute bottom-10 left-10 h-[250px] w-[400px] bg-cyber-indigo/5 blur-[100px] rounded-full pointer-events-none z-0"></div>

            {/* Static top Header */}
            <Header />

            {/* Content Canvas */}
            <main className="flex-1 pt-16 z-10 w-full overflow-y-auto">
              {children}
            </main>
          </div>
        </ProjectProvider>
      </body>
    </html>
  );
}
