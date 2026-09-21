---
title: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
url: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
source: developers.google.com
crawled: 2026-09-19 00:39:54
---

---
title: "SEO Starter Guide: The Basics | Google Search Central | Documentation | Google for Developers"
url: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
hostname: google.com
description: A knowledge of basic SEO can have a noticeable impact. Explore the Google SEO starter guide for an overview of search engine optimization essentials.
sitename: Google for Developers
date: "2025-12-10"
---
# Search Engine Optimization (SEO) Starter Guide

When you built your website, you likely created it with your users in mind, trying to make it easy for them to find and explore your content. One of those users is a search engine, which helps people discover your content. SEO—short for search engine optimization—is about helping search engines understand your content, and helping users find your site and make a decision about whether they should visit your site through a search engine.

  The Search Essentials outline the most important elements of
  what makes your website eligible to appear on Google Search. While there's no guarantee that any
  particular site will be added to Google's index, sites that follow the  **Search Essentials are
  more likely to show up in Google's search results**. SEO is about taking the next step and
  **working on improving your site's presence in Search**. This guide will walk you through some
  of the most common and effective improvements you can do on your site.

There are no secrets here that'll automatically rank your site first in Google (sorry!). In fact some of the suggestions might not even apply to your business, but following the best practices will hopefully make it easier for search engines (not just Google) to crawl, index, and understand your content.

## How does Google Search work?

Google is a fully automated search engine that uses programs called crawlers to explore the web constantly, looking for pages to add to our index. You usually don't need to do anything except publish your site on the web. In fact, the vast majority of sites listed in our results are found and added automatically as we crawl the web. If you're hungry for more, we have documentation about how Google discovers, crawls, and serves web pages.

## How long until I see impact in search results?

Every change you make will take some time to be reflected on Google's end. Some changes might take effect in a few hours, others could take several months. In general, you likely want to wait a few weeks to assess whether your work had beneficial effects in Google Search results. Keep in mind that not all changes you make to your website will result in noticeable impact in search results; if you're not satisfied with your results and your business strategies allow it, try iterating with the changes and see if they make a difference.

## Help Google find your content

  Before you actually do anything mentioned in this section, check if Google has already found your
  content (maybe you don't need to do anything!). Try searching on Google for your site with the
  `site: search operator`.
  If you see results pointing to your site, you're in the index. For example, a search for `site:wikipedia.org` returns
  these results.
  If you don't see your site, check out the technical requirements
  to make sure there's nothing technically preventing your site from showing in Google Search, and
  then come back here.

Google primarily finds pages through links from other pages it already crawled. In many cases, these are other websites that are linking to your pages. Other sites linking to you is something that happens naturally over time, and you can also encourage people to discover your content by promoting your site.

If you're open to a little technical challenge, you could also submit a sitemap—which is a file that contains all the URLs on your site that you care about. Some content management systems (CMS) may even do this automatically for you. However this isn't required, and you should first focus on making sure people know about your site.

### Check if Google can see your page the same way a user does

When Google crawls a page, it should ideally see the page the same way an average user does. For this, Google needs to be able to access the same resources as the user's browser. If your site is hiding important components that make up your website (like CSS and JavaScript), Google might not be able to understand your pages, which means they might not show up in search results or rank well for the terms you're targeting.

If your pages have different information depending on the user's physical location, make sure you're satisfied with the information that Google sees from its crawler's location, which is generally the US.

To check how Google sees your page, use the URL Inspection Tool in Search Console.

### Don't want a page in Google's search results?

It might be important for you to opt out your site as a whole or sections of it from appearing in search results. For example, you might not want your posts about your new embarrassing haircut to show up in search results. Google supports various ways that lets you opt out of crawling and indexing of your URLs. If you need to block some files, directories, or even your whole site from Google Search, check out our guide about ways to prevent content from appearing in search results.

## Organize your site

When you're setting up or redoing your site, it can be good to organize it in a logical way because it can help search engines and users understand how your pages relate to the rest of your site. Don't drop everything and start reorganizing your site right now though: while these suggestions can be helpful long term (especially if you're working on a larger website), search engines will likely understand your pages as they are right now, regardless of how your site is organized.

### Use descriptive URLs

Parts of the URL can be displayed in search results as breadcrumbs, so users can also use the URLs to understand whether a result will be useful for them.

Google learns breadcrumbs automatically based on the words in the URL, but you can also influence them with structured data if you like a technical challenge. Try to include words in the URL that may be useful for users; for example:

`https://www.example.com/pets/cats.html`

A URL that only contains random identifiers is less helpful for users; for example:

`https://www.example.com/2/6772756D707920636174`

### Group topically similar pages in directories

If you have more than a few thousand URLs on your site, how you organize your content may have effects on how Google crawls and indexes your site. Specifically, using directories (or folders) to group similar topics can help Google learn how often the URLs in individual directories change.

For example, consider the following URLs:

`https://www.example.com/policies/return-policy.html`

  `https://www.example.com/promotions/new-promos.html`

  The content in the `policies` directory seldomly changes, however the content in the
  `promotions` directory likely changes very often. Google can learn this information
  and crawl the different directories at different frequencies. To learn more about search-friendly
  site structures, check out our guide for ecommerce sites,
  for which a good URL structure is more important as they tend to be larger.

### Reduce duplicate content

  Some websites show the same content under different URLs, which is called *duplicate content*.
  Search engines choose a single URL (the *canonical* URL) to show users, per piece of content.

Having duplicate content on your site is not a violation of our spam policies, but it can be a bad user experience and search engines might waste crawling resources on URLs that you don't even care about. If you're feeling adventurous, it's worth figuring out if you can specify a canonical version for your pages. But if you don't canonicalize your URLs yourself, Google will try to automatically do it for you.

When working on canonicalization, try to ensure that each piece of content on your site is only accessible through one individual URL; having two pages that contain the same information about your promotions can be a confusing user experience (for example, people might wonder which is the right page, and whether there's a difference between the two).

  If you have multiple pages that have the same information, try setting up a
  redirect from non-preferred URLs to a
   URL that best represents that information. If you can't redirect, use the
  `rel="canonical"`
  `link` element instead. But again, don't worry too much about this;
   search engines can generally figure this out for you on their own most of the time.

## Make your site interesting and useful

Creating content that people find compelling and useful will likely influence your website's presence in search results more than any of the other suggestions in this guide. While "compelling and useful content" can mean different things to different people, content like this generally shares some common attributes, such as:

- **The text is easy-to-read and well organized** : Write content naturally and make sure the
    content is well written, easy to follow, and free of spelling and grammatical mistakes. Break
    up long content into paragraphs and sections, and provide headings to help users navigate your
    pages.
- **The content is unique** :
    When you're writing new content, don't copy others' content in part or in its entirety: create
    the content yourself based on what you know about the topic. Don't just rehash what others
    already published.
- **The content is up-to-date** : Check in on previously published content and update it as
    needed, or even delete it if it's not relevant anymore.
- **The content is helpful, reliable, and people-first:** Be sure that you're writing content that your readers will find helpful and reliable. For
    example, providing expert or experienced sources can help people understand your articles' expertise.

### Expect your readers' search terms

Think about the words that a user might search for to find a piece of your content. Users who know a lot about the topic might use different keywords in their search queries than someone who is new to the topic. For example, some users might search for "charcuterie", while others might search for "cheese board". Anticipating these differences in search behavior and writing with your readers in mind could produce positive effects on how your site performs in search results.

However, don't worry if you don't anticipate every variation of how someone might seek your content. Google's language matching systems are sophisticated and can understand how your page relates to many queries, even if you don't explicitly use the exact terms in them.

### Avoid distracting advertisements

While ads are a part of the internet and are meant to be seen by users, don't let them become overly distracting or prevent your users from reading your content. For example, advertisements, or interstitial pages (pages displayed before or after the content you're expecting) that make it difficult to use the website.

### Link to relevant resources

Links are a great way to connect your users and search engines to other parts of your site, or relevant pages on other sites. In fact, the vast majority of the new pages Google finds every day are through links, making links a crucial resource you need to consider to help your pages be discovered by Google and potentially shown in search results. Additionally, links can also add value by connecting users (and Google) to another resource that corroborates what you're writing about.

#### Write good link text

  *Link text* (also known as *anchor text*)  is the text part of a link that you can see.
   This text tells users and Google something about the page you're linking to. With
  appropriate anchor text,
  users and search engines can easily understand what your linked pages contain before they visit.
  

#### Link when you need to

  Links can provide more context on a topic, both for users and search engines, which may help
  demonstrate your knowledge on a topic. However when you're linking to pages outside of your
  control, for example content on other sites, make sure you trust the resource you're linking to.
  If you can't trust the content and you still want to link to them, add a
  `nofollow` or similar annotation
  to the link to avoid search engines associating your site with the site you're linking to. This
  helps avoid potential negative consequences in your rankings in Google Search.

  If you're accepting user-generated content on your site, such as forum posts or comments, make
  sure every link that's posted by users has a `nofollow` or similar annotation
  automatically added by your CMS. Since you're not creating the content in this case, you likely
  don't want your site to be blindly associated with the sites users are linking to. This can also
  help discourage spammers from abusing your website.

## Influence how your site looks in Google Search

  A typical Google Search results page consists of a
  few different visual elements that
  you can influence to help users decide whether they should visit your site through those search
  results. In this section, we're focusing on the *title link* and the *snippet* because
  these are the more visually significant elements.

### Influence your title links

  The *title link* is the headline part of the search result and it can help people decide
  which search result to click. There are a few sources that Google uses to generate this title
  link, including the words inside the `<title>` element (also called the title
  text) and other headings on the page. This title text can also be used for the title that's shown
  in browsers and bookmarks.

You can influence the title links in Search by writing good titles: a good title is unique to the page, clear and concise, and accurately describes the contents of the page. For example, your title could include the name of your website or business, other bits of important information like the physical location of the business, and maybe some information about what the particular page has to offer for users. Our documentation about title links has more tips about how to create good titles and how to influence your site's search results' title links.

### Control your snippets

  Below the title link, a search result typically has a description of the target page to help users
  decide whether they should click the search result. This is called a *snippet*.

The snippet is sourced from the actual content of the page the search result is linking to, thus you have complete control over the words that can be used to generate the snippet. Occasionally the snippet may be sourced from the contents of the meta description tag, which is typically a succinct, one- or two-sentence summary of the page. A good meta description is short, unique to one particular page, and includes the most relevant points of the page. Check out our tips for writing good meta descriptions for more inspiration.

## Add images to your site, and optimize them

Many people search visually, and images can be how people find your website for the first time. For example, if you have a recipe blog, people might find your content by searching for "fruit tart recipes" and browsing photos of various types of fruit tarts.

As you add images to your site, make sure that people and search engines can find and understand them.

### Add high-quality images near relevant text

When you use high quality images, you give users enough context and detail to decide which image best matches what they were looking for. For example, if people are looking for "daisies" and come across a rogue edelweiss in search results, a higher quality image would help them distinguish the type of flower.

Use images that are sharp and clear, and place them near text that's relevant to the image. The text that's near images can help Google better understand what the image is about and what it means in context to your page.

For example, if the page is reviewing yarn shops in London, then it would make sense to embed one of your photos of the yarn shop in the section that details the location, description, and review information for that yarn shop. This helps Google and users associate the image with text that provides more context to what the page is about.

### Add descriptive alt text to the image

  Alt text is a short, but descriptive piece of text that explains the relationship between the
  image and your content. It helps search engines understand what your image is about and the
  context of how your image relates to your page, so writing good alt text
  is quite important. You can add this to your HTML with the `alt` attribute of the
  `img` element, or your CMS may have an easy way to specify a description for an image
  when you're uploading it to your site. Learn more about how to write good alt text,
  and how to add it to your images.

## Optimize your videos

If your website includes pages that are primarily about individual videos, people may also be able to discover your site through video results in Google Search. Many of the best practices for images and text also apply to videos:

- Create high-quality video content, and embed the video on a standalone page, near text that's relevant to that video.
- Write descriptive text in the titles and description fields of a video (the title of a video is still a title, and so you can apply the best practices for writing titles here too).

If your site is particularly video-focused, then continue reading about more things you can do to optimize your videos for search engines.

## Promote your website

Effectively promoting your new content will lead to faster discovery by those who are interested in the same subject, and also by search engines. You can do this in many ways:

- Social media promotion
- Community engagement
- Advertisement, both offline and online
- Word of mouth, and many other methods

One of the most effective and lasting ways is word of mouth: that is, people familiar with your site tell their friends about it, who in turn visit your site. This can take time, and usually you need to invest some time and effort in other practices first, such as community engagement. Our friends over at Google for Creators have excellent resources about building and engaging your audience.

Putting effort into the offline promotion of your company or site can also be rewarding. For example, if you have a business site, make sure its URL is listed on your business cards, letterhead, posters, and other materials. With their permission, you could also send out recurring newsletters to your audience letting them know about new content on your website.

As with everything in life, you can overdo promoting your site and actually harm it: people may get fatigued of your promotions, and search engines may perceive some of the practices as manipulation of search results.

## Things we believe you shouldn't focus on

As SEO has evolved, so have the ideas and practices (and at times, misconceptions) related to it. What was considered best practice or top priority in the past may no longer be relevant or effective due to the way search engines (and the internet) have developed over time.

To help you focus on the things that are actually important when it comes to SEO, we collected some of the most common and prominent topics we've seen circulating the internet. In general, our message on these topics is that you should do what's best for your business area; we will elaborate on a few specific points here:

|  |  |  | 

## Next steps

- **Get started with Search Console** : Setting up a Search Console account helps you monitor
     and optimize how your website performs on Google Search. Learn how to
    set up your account and what reports to check out first.
- **Maintain your website's SEO over time** : Learn more about
    managing your site's presence in the long term,
    including more in-depth SEO tasks and scenarios, such as preparing for a site move, or managing
    a multi-lingual site.
- **Enhance how your site looks in Google Search results** : Valid
    structured data on
    your pages also makes your pages eligible for many special features in Google Search results,
    including review stars, carousels, and more. Explore the
    gallery of search result types
    that your page can be eligible for.

### Stay informed and ask questions

As you embark on your SEO journey, here are some resources that can help you stay on top of changes and new resources we publish:

|  |  |  |