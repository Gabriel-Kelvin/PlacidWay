# Source review and implementation decisions

Reviewed the complete assessment document and all seven allowlisted HTML pages on 9 October 2026. The user's instruction postpones deployment and the seven-day public availability demonstration. No email submission, public publication, or extra crawling is authorized by the assessment document itself.

The source snapshot lives in `data/knowledge.json`. Evidence IDs refer to whitespace-normalized visible text, with table cells joined by ` | ` and table rows kept intact. These are snapshot line numbers, not the publisher's HTML line numbers. Snapshot hashes make an old citation auditable after a refresh.

| Source | What it contains | Important boundaries |
|---|---|---|
| ITC clinic profile | Founder Dr. Carlos Bautista, Tijuana location, medical team, services, travel information, base pricing, eligibility process, risks, testimonials | Marketing and testimonial claims are attributed to the publisher. They are not independent clinical evidence. Appointment widgets, timezone menus, recommendations, and footer accreditation logos are excluded. |
| Adenocarcinoma package | Glandular-cancer package; three-week outpatient and inpatient tiers; detailed inclusions, add-ons, exclusions, itinerary, FAQs | Never substitute adrenal or anal package details. The three-month post-discharge consultation is not recovery duration. |
| Adrenal package | Endocrine/adrenal focus; the same two price tiers with distinct wording; hormone-management FAQ, admission review of supplements | A source FAQ saying a therapy can be combined with other care does not authorize personal advice. |
| Anal cancer package | Distinct package; two tiers, exclusions, family/companion FAQ, colostomy-related FAQ | No personal suitability or safety conclusions, including for patients with a colostomy. |
| ITC videos | Page titles, categories, and short clinic introduction | No transcripts were supplied. The bot may name the titles and link the videos page, but cannot describe scenes, dialogue, outcomes, or timecodes. |
| ITC price list | USD 18,995 entries for breast, prostate, lung, pancreatic, colorectal and colon cancer; one unlabeled row | Unlabeled rows do not identify a treatment. These prices do not supply every package inclusion. |
| Alternative medicine price comparison | Broad category ranges, procedure ranges, cost components, named clinic rows, general inclusion/exclusion descriptions, FAQs and disclaimer | Category averages and USD 35 minimum cannot be assigned to cancer packages. USD 50 is the lower end of a general consultation component, not the cancer-treatment price. Country comparisons require the same procedure in both locations. |

## Price audit

Each of the three package pages identifies the displayed package price as **starting from**, and gives this explicit table:

- Out-Patient Program: **3 Weeks, USD 18,995**.
- In-Patient Program: **3 Weeks, USD 30,000**.

Outpatient inclusions include weekly labs, one prescribed imaging study of one area, program therapies, two meals during treatment hours, standard protocol medication, and a consultation after three months. Inpatient inclusions add continuous supervision and private accommodation with three daily meals. Wording differs by package and is retained per source.

Optional procedures include LAK cells, specific killer cell antibody, ethanol tumor ablation, MCA, and intratumoral immunotherapy. They are additional costs. Exclusions include certain medications, external specialists, surgeries/biopsies, blood products, ambulance/emergency costs, extra imaging and home programs. Do not imply the base price is an all-in final quote.

The comparison page contains a valid same-procedure example: Ozone Therapy at Fizikon Medical Center in Konya, Turkey, listed at USD 110, and Stem Health Guadalajara in Zapopan, Mexico, listed at USD 1,000. The bot quotes the individual clinic rows and cautions that package scope varies. It does not generalize those listings into a national average or claim clinical equivalence.

## Extraction and crawl review

Robots.txt allows the seven paths. The crawler identifies itself as `PlacidWayAssessmentBot/1.0`, waits at least 1.05 seconds between requests, observes a longer published crawl delay, and never follows related-page links. Robots failure stops refresh requests. Redirects are not followed automatically. Source failures retain old snapshots and mark them with a warning.

Page-specific selectors retain the main editorial content and table rows. Normalized content hashes prevent unchanged pages from being treated as new versions. ETags and Last-Modified headers are used when supplied. More than 45% content loss is treated as a possible extraction failure requiring review.

## Medical boundary

The pages include strong claims such as non-toxic care, cancer remission and safety. The assistant cannot independently verify those claims from these seven sources. It refuses questions about diagnosis, efficacy, cure, personal suitability, dosage and stopping conventional care. Source attribution is not a claim of medical validation.

## Assessment test substitutions

The eight required types use the adrenal package in Mexico for cost, ozone therapy in Turkey versus Mexico for comparison, the adenocarcinoma outpatient package for inclusions, and a recovery follow-up to adenocarcinoma. The other four questions preserve the assessment wording. The wrong-price case carries an explicit adrenal conversation context; without a treatment context, the assistant asks which treatment is meant.
