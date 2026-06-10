import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="mt-24 border-t border-white/10 bg-[var(--color-bg-deep)] py-12 text-[14px] text-[var(--color-text-muted)]">
      <div className="mx-auto max-w-page px-4 md:px-8 lg:px-[60px]">
        <div className="mb-6 text-[var(--color-text-secondary)]">
          {t("footer.questions")}
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">{t("footer.faq")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.investor_relations")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.privacy")}</Link></li>
          </ul>
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">{t("footer.help_centre")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.jobs")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.cookie_preferences")}</Link></li>
          </ul>
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">{t("footer.account")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.ways_to_watch")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.corporate_information")}</Link></li>
          </ul>
          <ul className="space-y-3">
            <li><Link to="#" className="hover:underline">{t("footer.media_centre")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.terms_of_use")}</Link></li>
            <li><Link to="#" className="hover:underline">{t("footer.contact_us")}</Link></li>
          </ul>
        </div>
        <div className="mt-10 text-xs">{t("footer.copyright")}</div>
      </div>
    </footer>
  );
}
