---
title: Control the Content You Share on Search | Google Search Central | Documentation | Google for Developers
url: https://developers.google.com/search/docs/crawling-indexing/control-what-you-share
hostname: google.com
description: You can control what content Google sees on your site and what is shown in search results. Discover the main ways to remove site content from Google.
sitename: Google for Developers
date: "2025-12-10"
---
# Control what you share with Google

Google supports a variety of ways that allows site owners control what shows up in Google's search results. While most people focus on getting their pages indexed, sometimes it's important to do the opposite: prevent content from appearing in Search. There are a few reasons you might want to hide content from Google:

- 
    **To restrict data** : You might have data hosted on your site that you want to show
    only to users who are already on your site. You can block Google from crawling such data so
    it doesn't show up in search results.
Also keep in mind that certain files published on your site may have metadata that can show up in Search. Learn more about keeping redacted information out of Search.
- 
    **To hide content of less value to your audience** : Your website might have low quality
    content that shouldn't show up in Search. For example, if your website allows users to
    create content, some of that content might be
    low quality or even spam.
    Allowing indexing of such content may have a negative effect on your site's ranking in
    Google's search results.
- 
    **To have Google focus on your important content** : If you have a very large site (over
    hundreds of thousands of URLs) and pages with less important content, or if you have a lot
    of duplicate content, you might want to prevent Google from crawling the duplicate or less
    important pages in order to focus on your more important content.

## How to block content

Here are the main ways to block content from appearing in Google:

| Methods |  | 
|---|---|
| Remove the content from your site |          **Applicable: all content types** Removing content from your site is the best way to ensure that it won't appear in Google Search and anywhere else on the Internet. | 
| Password-protect your files |          **Applicable: all content types** If you have confidential or private content on your site, you need to password protect it to ensure only authorized users can access it. This will also prevent that content from appearing in Google Search, or if it already appears, it will eventually remove that content from our search results. | 
| `noindex` rule |          **Applicable: all content types**          The `noindex` robots`meta` tag is a         rule that tells Google not to index your content or let it appear in Google search         results. Your content can still be linked to and visited through other web pages, or         directly visited by users with a link, but the content will not appear in Google search         results. | 
| Disallow crawling with robots.txt |          **Applicable: images and video** Google only indexes images and videos that Googlebot is allowed to crawl. To prevent Googlebot from accessing your media files, use robots.txt rules to block the files. | 
| Opt out of specific Google properties |          **Applicable: web pages** You can tell Google not to include content from your site in specific Google properties, such as Google Shopping, Google Hotels, and vacation rentals. | 

## Remove existing content from Google

If the content hosted on your site is already appearing in Google, you can request the removal of those search results. Learn how to remove a page hosted on your site from Google.