import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-white/10 bg-[var(--color-bg-deep)] py-12 text-[14px] text-[var(--color-text-muted)]">
      <div className="mx-auto max-w-page px-4 md:px-8 lg:px-[60px]">
        <div className="mb-6 text-[var(--color-text-secondary)]">
          Questions? Contact us.
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">FAQ</Link></li>
            <li><Link to="#" className="hover:underline">Investor Relations</Link></li>
            <li><Link to="#" className="hover:underline">Privacy</Link></li>
          </ul>
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">Help Centre</Link></li>
            <li><Link to="#" className="hover:underline">Jobs</Link></li>
            <li><Link to="#" className="hover:underline">Cookie Preferences</Link></li>
          </ul>
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">Account</Link></li>
            <li><Link to="#" className="hover:underline">Ways to Watch</Link></li>
            <li><Link to="#" className="hover:underline">Corporate Information</Link></li>
          </ul>
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">Media Centre</Link></li>
            <li><Link to="#" className="hover:underline">Terms of Use</Link></li>
            <li><Link to="#" className="hover:underline">Contact Us</Link></li>
          </ul>
        </div>
        <div className="mt-10 text-xs">© 2026 Anjaneya OTT</div>
      </div>
    </footer>
  );
}
