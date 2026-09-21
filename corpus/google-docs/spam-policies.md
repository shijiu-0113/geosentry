---
title: Spam policies for Google web search
url: https://developers.google.com/search/docs/essentials/spam-policies
source: developers.google.com
---
# Spam policies for Google web search

> 来源：https://developers.google.com/search/docs/essentials/spam-policies
> 更新时间：2026-08-28 UTC

In the context of Google Search, spam refers to techniques used to deceive users or manipulate our Search systems into featuring content prominently, such as attempting to manipulate Search systems into ranking content highly or attempting to manipulate generative AI responses in Google Search. Our spam policies help protect users and improve the quality of Search results. To be eligible to appear in Google web search results, content (web pages, images, videos, news content or other material that Google finds from across the web) shouldn't violate Google Search's overall policies or the spam policies listed on this page. These policies apply to all web search results, including those from Google's own properties.

We detect policy-violating practices both through automated systems and, as needed, human review that can result in a manual action. Sites that violate our policies may rank lower in results or not appear in results at all.

If you believe that a site is violating Google's spam policies, let us know by filing a search quality user report. We're focused on developing scalable and automated solutions to problems, and we'll use these reports to further improve our spam detection systems.

## Cloaking

Cloaking refers to the practice of presenting different content to users and search engines with the intent to manipulate search rankings and mislead users. Examples of cloaking include:

- Showing a page about travel destinations to search engines while showing a page about discount drugs to users
- Inserting text or keywords into a page only when the user agent that is requesting the page is a search engine, not a human visitor

If your site uses technologies that search engines have difficulty accessing, like JavaScript or images, see our recommendations for making that content accessible to search engines and users without cloaking.

If you operate a paywall or a content-gating mechanism, we don't consider this to be cloaking if Google can see the full content of what's behind the paywall just like any person who has access to the gated material and if you follow our Flexible Sampling general guidance.

## Doorway abuse

Doorway abuse is when sites or pages are created to rank for specific, similar search queries. They lead users to intermediate pages that aren't as useful as the final destination. Examples of doorway abuse include:

- Having multiple websites with slight variations to the URL and home page to maximize their reach for any specific query
- Having multiple domain names or pages targeted at specific regions or cities that funnel users to one page
- Generating pages to funnel visitors into the actual usable or relevant portion of a site
- Creating substantially similar pages that are closer to search results than a clearly defined, browseable hierarchy

## Expired domain abuse

Expired domain abuse is where an expired domain name is purchased and repurposed primarily to manipulate search rankings by hosting content that provides little to no value to users. Illustrative examples include, but aren't limited to:

- Affiliate content on a site previously used by a government agency
- Commercial medical products being sold on a site previously used by a non-profit medical charity
- Casino-related content on a former elementary school site

## Hacked content

Hacked content is any content placed on a site without permission, due to vulnerabilities in a site's security. Hacked content gives poor search results to our users and can potentially install malicious content on their machines. Examples of hacking include:

- **Code injection**: When hackers gain access to your website, they might try to inject malicious code into existing pages on your site. This often takes the form of malicious JavaScript injected directly into the site, or into iframes.
- **Page injection**: Sometimes, due to security flaws, hackers are able to add new pages to your site that contain spammy or malicious content. These pages are often meant to manipulate search engines or to attempt phishing.
- **Content injection**: Hackers might also try to subtly manipulate existing pages on your site. Their goal is to add content to your site that search engines can see but which may be harder for you and your users to spot. This can involve adding hidden links or hidden text to a page by using CSS or HTML, or it can involve more complex changes like cloaking.
- **Redirects**: Hackers might inject malicious code to your website that redirects some users to harmful or spammy pages. The kind of redirect sometimes depends on the referrer, user agent, or device.

## Hidden text and link abuse

Hidden text or link abuse is the practice of placing content on a page in a way solely to manipulate search engines and not to be easily viewable by human visitors. Examples of hidden text or link abuse include:

- Using white text on a white background
- Hiding text behind an image
- Using CSS to position text off-screen
- Setting the font size or opacity to 0
- Hiding a link by only linking one small character

There are many web design elements today that utilize showing and hiding content in a dynamic way to improve user experience; these elements don't violate our policies: accordion or tabbed content, slideshow or slider, tooltip or similar text that displays additional content when users interact over an element, text that's only accessible to screen readers.

## Keyword stuffing

Keyword stuffing refers to the practice of filling a web page with keywords or numbers in an attempt to manipulate rankings in Google Search results. Often these keywords appear in a list or group, unnaturally, or out of context. Examples of keyword stuffing include:

- Lists of phone numbers without substantial added value
- Blocks of text that list cities and regions that a web page is trying to rank for
- Repeating the same words or phrases so often that it sounds unnatural

## Link spam

Link spam is the practice of creating links to or from a site primarily for the purpose of manipulating search rankings. The following are examples of link spam:

- Buying or selling links for ranking purposes (exchanging money, goods or services for links; sending someone a product in exchange for a link)
- Excessive link exchanges ("Link to me and I'll link to you") or partner pages exclusively for the sake of cross-linking
- Using automated programs or services to create links to your site
- Requiring a link as part of a Terms of Service, contract, or similar arrangement without allowing a third-party content owner the choice of qualifying the outbound link
- Text advertisements or text links that don't block ranking credit
- Advertorials or native advertising where payment is received for articles that include links that pass ranking credit
- Low-quality directory or bookmark site links
- Keyword-rich, hidden, or low-quality links embedded in widgets distributed across various sites
- Widely distributed links in the footers or templates of various sites
- Forum comments with optimized links in the post or signature
- Creating low-value content primarily for the purposes of manipulating linking and ranking signals

Google does understand that buying and selling links is a normal part of the economy of the web for advertising and sponsorship purposes. It's not a violation of our policies to have such links as long as they are qualified with a `rel="nofollow"` or `rel="sponsored"` attribute value to the `<a>` tag.

## Machine-generated traffic

Machine-generated traffic (also called automated traffic) refers to the practice of sending automated queries to Google. This includes scraping results for rank-checking purposes or other types of automated access to Google Search conducted without express permission. Machine-generated traffic consumes resources and interferes with our ability to best serve users. Such activities violate our spam policies and the Google Terms of Service.

## Malicious practices

Malicious practices create a mismatch between user expectations and the actual outcome, leading to a negative and deceptive user experience, or compromised user security or privacy. Common examples:

- **Malware**: any software or mobile application specifically designed to harm a computer, a mobile device, the software it's running, or its users.
- **Unwanted software**: an executable file or mobile application that engages in behavior that is deceptive, unexpected, or that negatively affects the user's browsing or computing experience.
- **Back button hijacking**: when a site interferes with user browser navigation by manipulating the browser history or other functionalities, preventing them from using their back button to immediately get back to the page they came from.

## Misleading functionality

Misleading functionality refers to the practice of intentionally creating sites that trick users into thinking they would be able to access some content or services but in reality can't. Examples include a site with a fake generator that claims to provide app store credit but doesn't actually provide the credit, or a site that claims to provide certain functionality (PDF merge, countdown timer, online dictionary service) but intentionally leads users to deceptive ads.

## Scaled content abuse

Scaled content abuse is when many pages are generated for the primary purpose of manipulating search rankings and not helping users. This abusive practice is typically focused on creating large amounts of unoriginal content that provides little to no value to users, no matter how it's created. Examples include, but aren't limited to:

- Using generative AI tools or other similar tools to generate many pages without adding value for users
- Scraping feeds, search results, or other content to generate many pages (including through automated transformations like synonymizing, translating, or other obfuscation techniques), where little value is provided to users
- Stitching or combining content from different web pages without adding value
- Creating multiple sites with the intent of hiding the scaled nature of the content
- Creating many pages where the content makes little or no sense to a reader but contains search keywords

## Scraping

Scraping refers to the practice of taking content from other sites, often through automated means, and hosting it with the purpose of manipulating search rankings. Examples of abusive scraping include:

- Republishing content from other sites without adding any original content or value, or even citing the original source
- Copying content from other sites, modifying it only slightly (for example, by substituting synonyms or using automated techniques), and republishing it
- Reproducing content feeds from other sites without providing some type of unique benefit to the user
- Creating sites dedicated to embedding or compiling content, such as videos, images, or other media from other sites, without substantial added value to the user

## Site reputation policy

The site reputation policy applies where third-party content is published on a host site mainly because of that host's already-established ranking signals, which it has earned primarily from its first-party content. The goal of this tactic is for the content to rank better than it could otherwise on its own. We have made changes applicable to the policy in the European Economic Area (EEA).

*Third-party content* is content that's created by an entity that's separate from the established host site. Examples of separate entities include users of that site, freelancers, white-label services, and content created by people not employed directly by the host site.

Having third-party content alone isn't inconsistent with the site reputation policy; it's only inconsistent if the third-party content is published on a host site mainly because of that host site's already-established ranking signals.

Examples inconsistent with the site reputation policy include, but aren't limited to:

- An educational site hosting a page about sponsored reviews of payday loans written by a third-party that distributes the same page to other sites across the web
- A medical site hosting a low-quality, third-party advertising page about "best casinos" that isn't integrated with the site

Examples that are **NOT** considered inconsistent with the site reputation policy include:

- Wire service or press release service sites
- News publications that have syndicated news content from other news publications
- Sites designed to allow user-generated content, such as a forum website or comment sections
- Columns, opinion pieces, articles, and other work of an editorial nature
- Third-party content (for example, "advertorial" or "native advertising" type pages) where the purpose is to share content directly to readers, rather than hosting the content to manipulate search rankings
- Using affiliate links throughout a page, with links treated appropriately, or embedding third-party ad units throughout a page

Google generally applies a presumption that individual pages (including new pages) match the overall quality of other pages on the domain. If we detect that a portion of your site may be out of line with this policy, a site will be subject to human review. As part of this review, if the site is found to be inconsistent with the policy, the consequences for the way the site's pages appear in search results will vary depending on the location of users.

- **Outside the EEA**: If a site is found to be out of line with this policy, the relevant pages may be subject to a manual action when they appear in Search results shown to users outside the EEA.
- **Within the EEA**: When pages appear in Search results shown to users within the EEA, the relevant pages may be categorized as separate from the main domain but won't be subject to the impact of manual action. This will allow the different parts of the site to rank independently of each other, on their own merits.

If your site is affected in this way, we will notify you in the Manual actions report and in the Search Console message center. All sites will have the opportunity to address this issue or appeal via a reconsideration request.

### More detailed guidance

On the rare occasions where we perform a human review, our overarching goal is to determine whether content on the relevant portion of the site is created with sufficient input, editorial oversight, or contribution from the host site to be considered fully integrated with the main site. The review takes into account objective factors:

- **How the content is presented**: are the graphic design, formatting, typography and UX features consistent with the host domain?
- **The quality of the content**: are there quality issues present on the page that don't appear on the main domain?
- **Its stated or implied authorship**: is there an explicit acknowledgement of ownership or responsibility for the content?
- **Does the content appear on multiple other sites in identical or near-identical form?**

Not one of these factors is either necessary or sufficient on its own. Based on the particular situation, some factors may be more relevant than others.

Example — unlikely to take action: an integrated coupons/deals section in partnership with a specialist provider, under a sub-folder fully integrated in the homepage, commercial character clearly disclosed, disclaimers identifying the publisher as editorially responsible, codes cross-referred in editorial content, easily navigable, and a contact/reporting link available.

Example — likely to take action: a globally recognized business publication hosts an unauthored affiliate article (links to a marketplace selling CBD oils) with no author or responsible editor identified, no disclaimers about commercial character, not part of any thematic section, no links from the main page, and content purely duplicating third-party material.

Example — unlikely to take action: a news site develops a new cooking section with affiliate links, content produced by a freelancer interviewing chefs with clear editorial oversight by the host publication, site branded consistently, clear statements of editorial responsibility, freelancer identified as author.

### FAQ

**Will manual action taken outside the EEA affect the ranking of my site within the EEA?**
No. Manual actions involving the site reputation policy outside the EEA only affect results shown to users outside the EEA. There's no obligation to apply a `noindex` tag to content that is subject to a manual action outside the EEA.

**A portion of my site was previously subject to manual action under this policy in the EEA. What happens now?**
Google will lift all previous manual actions taken under this policy for pages appearing in search results for users in the EEA. Those pages may be categorized as separate from the main domain and ranked on their own merits, but this isn't automatic.

**What happens when a part of my site is categorized as separate from the main domain?**
This categorization tells our systems that the presumption that individual pages match the overall quality of other pages on the domain no longer applies. It doesn't mean the separate portion immediately loses the ranking signals of the main site; over time, our ranking systems learn to rank these parts independently.

**What can I do if I disagree with the action taken on the domain?**
For websites in the EEA, a new reconsideration request process is available, and you can also make use of alternative dispute resolution.

## Sneaky redirects

Redirecting is the act of sending a visitor to a different URL than the one they initially requested. Sneaky redirecting is the practice of doing this maliciously in order to either show users and search engines different content or show users unexpected content that doesn't fulfill their original needs. Examples of sneaky redirects include:

- Showing search engines one type of content while redirecting users to something significantly different
- Showing desktop users a normal page while redirecting mobile users to a completely different spam domain

There are many legitimate, non-spam reasons to redirect one URL to another: moving your site to a new address, consolidating several pages into one, redirecting users to an internal page once they are logged in.

## Thin affiliation

Thin affiliation is the practice of publishing content with product affiliate links where the product descriptions and reviews are copied directly from the original merchant without any original content or added value. Affiliate pages can be considered thin if they are part of a program that distributes its content across a network of affiliates without providing additional value. Not every site that participates in an affiliate program is a thin affiliate: good affiliate sites add value by offering additional information about price, original product reviews, rigorous testing and ratings, navigation of products or categories, and product comparisons.

## User-generated spam

User-generated spam is spammy content added to a site by users through a channel intended for user content. Often site owners are unaware of the spammy content. Examples include spammy accounts on hosting services that anyone can register for, spammy posts on forum threads, comment spam on blogs, and spammy files uploaded to file hosting platforms.

## Other practices that can lead to demotion or removal

### Legal removals

When we receive a significant volume of valid copyright removal requests involving a given site, we are able to use that to demote other content from the site in our results. We apply similar demotion signals to complaints involving defamation, counterfeit goods, and court-ordered removals. In the case of child sexual abuse material (CSAM), we always remove such content when it is identified and we demote all content from sites with a significant proportion of CSAM content.

### Personal information removals

If we process a significant volume of personal information removals involving a site with exploitative removal practices, we demote other content from the site in our results. We may apply similar demotion practices for sites that receive a significant volume of removals of content involving doxxing content, explicit personal imagery created or shared without consent, or explicit non-consensual fake content.

### Policy circumvention

If a site continues to engage in actions intended to bypass our spam policies or content policies for Google Search, we may take appropriate action which may include restricting or removing eligibility for some of our search features (for example, Top Stories, Discover) and taking broader action in Google Search. Circumvention includes but isn't limited to using existing or creating new subdomains, subdirectories, or sites with the intention of continuing to violate our policies.

### Scam and fraud

Scam and fraud come in many forms, including but not limited to impersonating an official business or service through imposter sites, intentionally displaying false information about a business or service, or otherwise attracting users to a site on false pretenses. Examples include impersonating a well-known business or service provider to trick users into paying money to the wrong party, and creating deceptive sites pretending to provide official customer support on behalf of a legitimate business.

Last updated 2026-08-28 UTC.
