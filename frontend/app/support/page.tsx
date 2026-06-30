import React from "react";
import {
  HelpCircle,
  Mail,
  User,
  ShieldAlert,
  Server,
  Terminal,
  Activity,
  Compass,
  ArrowUpRight
} from "lucide-react";

const LinkedinIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);

export default function SupportPage() {
  const supportTeam = [
    {
      name: "Varun Kumar",
      role: "Backend Developer",
      email: "varun93545@gmail.com",
      linkedin: "https://www.linkedin.com/in/varun-kumar-835048345",
      specialty: "Backend APIs, database, and resume parser."
    },
    {
      name: "Piyush Yadav",
      role: "Frontend Developer",
      email: "piyushydv011@gmail.com",
      linkedin: "https://www.linkedin.com/in/piyushydv08/",
      specialty: "User interface, dashboard design, and page layouts."
    },
    {
      name: "Abhineet Mukharjee",
      role: "Full Stack Developer",
      email: "mukherjeeprakash17@gmail.com",
      linkedin: "https://www.linkedin.com/in/abhineet-mukherjee-456a83399?utm_source=share_via&utm_content=profile&utm_medium=member_ios",
      specialty: "Interview simulator, outreach system, and mock interviews."
    }
  ];

  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in text-left">
      {/* Header */}
      <header className="mb-10 border-b border-outline-variant/40 pb-6">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          Support <HelpCircle className="h-7 w-7 text-cyber-blue animate-pulse" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-2 font-mono leading-relaxed">
          If you have any questions or need assistance, feel free to reach out to our team.
        </p>
      </header>

      {/* Grid: Support Team Cards */}
      <section className="mb-12">
        <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-widest border-b border-outline-variant/60 pb-3 mb-6 flex items-center gap-2">
          <Activity className="h-4 w-4" />
          <span>Core Developers</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {supportTeam.map((member) => (
            <div key={member.name} className="bento-card rounded-lg p-6 flex flex-col justify-between gap-5 relative overflow-hidden group">
              {/* Top info */}
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center shrink-0">
                    <User className="h-5 w-5 text-cyber-blue" />
                  </div>
                  <div>
                    <h4 className="font-sans text-sm font-bold text-white leading-none group-hover:text-cyber-blue transition-colors">{member.name}</h4>
                    <span className="font-mono text-[9px] text-on-surface-variant uppercase tracking-wider block mt-1">{member.role}</span>
                  </div>
                </div>
                <div className="text-xs text-on-surface-variant space-y-2 leading-relaxed">
                  <p><strong>Primary Focus:</strong> {member.specialty}</p>
                </div>
              </div>

              {/* Action Links */}
              <div className="flex flex-col gap-2 pt-3 border-t border-outline-variant/30">
                {/* LinkedIn Link */}
                <a
                  href={member.linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 rounded border border-outline-variant bg-[#07070a]/50 text-xs font-mono text-on-surface hover:text-cyber-blue hover:border-cyber-blue/40 transition-colors"
                >
                  <LinkedinIcon className="h-3.5 w-3.5 text-cyber-blue" />
                  <span>LinkedIn Profile</span>
                  <ArrowUpRight className="h-3 w-3 ml-auto opacity-40 group-hover:opacity-100 transition-opacity" />
                </a>

                {/* Email Link */}
                <a
                  href={`mailto:${member.email}`}
                  className="flex items-center gap-2 px-3 py-2 rounded border border-outline-variant bg-[#07070a]/50 text-xs font-mono text-on-surface hover:text-cyber-blue hover:border-cyber-blue/40 transition-colors"
                >
                  <Mail className="h-3.5 w-3.5 text-cyber-blue" />
                  <span>{member.email}</span>
                  <ArrowUpRight className="h-3 w-3 ml-auto opacity-40 group-hover:opacity-100 transition-opacity" />
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>


    </div>
  );
}
