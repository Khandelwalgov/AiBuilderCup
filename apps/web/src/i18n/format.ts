const hindi: Record<string, string> = {
  active: 'काम चल रहा है',
  inactive: 'अभी काम बंद है',
  prelaunch: 'शुरू करने की तैयारी',
  unknown: 'अभी पता नहीं',
  education: 'शिक्षा',
  business: 'व्यवसाय',
  employment: 'रोज़गार',
  agriculture: 'कृषि',
  healthcare: 'स्वास्थ्य',
  procurement: 'खरीद',
  draft: 'मसौदा',
  published: 'प्रकाशित',
  rejected: 'अस्वीकृत',
  verified: 'समीक्षित',
  needs_review: 'समीक्षा आवश्यक',
  human_review_pending: 'मानवीय समीक्षा बाकी',
  processing_pending: 'प्रसंस्करण बाकी',
  needs_ocr: 'OCR समीक्षा आवश्यक',
  reviewed_and_published: 'समीक्षित और प्रकाशित',
  policy_guideline: 'नीति दिशानिर्देश',
  tender_notice: 'निविदा सूचना',
  general_announcement: 'सामान्य घोषणा',
  document_index: 'दस्तावेज़ सूची',
  amendment: 'संशोधन',
  unclassified: 'वर्गीकरण बाकी',
  irrelevant: 'अप्रासंगिक',
  source_unreachable: 'स्रोत उपलब्ध नहीं',
  discovered: 'खोजा गया',
  closed: 'बंद',
  superseded: 'पुराना संस्करण',
  owner: 'स्वामी',
  admin: 'प्रशासक',
  editor: 'संपादक',
  viewer: 'दर्शक',
  authorized: 'अधिकृत',
  not_shared: 'साझा नहीं',
  unregistered: 'अपंजीकृत',
  registered: 'पंजीकृत',
  company: 'कंपनी',
  partnership: 'साझेदारी',
  sole_proprietor: 'एकल स्वामित्व',
  succeeded: 'सफल',
  failed: 'विफल',
  unchanged: 'कोई बदलाव नहीं',
  pending: 'बाकी',
  running: 'चल रहा है',
};
export function displayLabel(value: string, hi: boolean) {
  return hi ? (hindi[value] ?? value.replaceAll('_', ' ')) : value.replaceAll('_', ' ');
}
export function displayDate(value: string | null | undefined, hi: boolean, fallback: string) {
  if (!value) return fallback;
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? fallback
    : date.toLocaleString(hi ? 'hi-IN' : 'en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
}
