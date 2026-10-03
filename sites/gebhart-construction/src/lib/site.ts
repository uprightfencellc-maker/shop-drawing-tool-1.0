import business from '../data/business.json';
import services from '../data/services.json';
import reviewData from '../data/reviews.json';
import projectData from '../data/projects.json';

export { business, services };
export const reviews = reviewData.reviews;
export const projects = projectData.projects;

export type Service = (typeof services)[number];
export type Review = (typeof reviews)[number];

export const telHref = `tel:${business.phone.e164}`;
export const smsHref = `sms:${business.phone.e164}`;
export const mailHref = `mailto:${business.email}`;

export const servicesByGroup = (group: 'Exterior' | 'Interior') =>
  services.filter((s) => s.group === group);

export const reviewsForService = (s: Service) =>
  reviews.filter((r) => r.tags.some((t) => s.reviewTags.includes(t)));

const fmtTime = (t: string) => {
  const [h, m] = t.split(':').map(Number);
  const suffix = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, '0')} ${suffix}`;
};

/** Hours rows. A `null` part means not confirmed by the client and renders as a TBD placeholder. */
export const hoursRows = business.hours.map((h) => ({
  days: h.days,
  closed: h.display === 'Closed',
  opens: h.opens ? fmtTime(h.opens) : null,
  closes: h.closes ? fmtTime(h.closes) : null,
}));

export const fullAddress = `${business.address.street}, ${business.address.city}, ${business.address.region} ${business.address.postalCode}`;

export const mapEmbedSrc = `https://www.google.com/maps?q=${encodeURIComponent(fullAddress)}&output=embed`;

export const formatMonth = (ym: string) => {
  const [y, m] = ym.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' });
};

/** Sitewide LocalBusiness JSON-LD. Only confirmed facts; hours are omitted until confirmed. */
export const businessJsonLd = (site: URL) => ({
  '@context': 'https://schema.org',
  '@type': 'HomeAndConstructionBusiness',
  '@id': new URL('/#business', site).href,
  name: business.name,
  url: site.href,
  telephone: business.phone.e164,
  email: business.email,
  image: new URL('/og-image.jpg', site).href,
  address: {
    '@type': 'PostalAddress',
    streetAddress: business.address.street,
    addressLocality: business.address.city,
    addressRegion: business.address.region,
    postalCode: business.address.postalCode,
    addressCountry: business.address.country,
  },
  paymentAccepted: 'Credit Card',
  aggregateRating: {
    '@type': 'AggregateRating',
    ratingValue: business.ratings.google.value,
    reviewCount: business.ratings.google.count,
    bestRating: 5,
  },
  sameAs: [business.social.facebook, business.social.instagram, business.ratings.angi.url],
});
