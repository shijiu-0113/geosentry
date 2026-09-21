---
title: Define Website Favicon for Search Results | Google Search Central | Documentation | Google for Developers
url: https://developers.google.com/search/docs/appearance/favicon-in-search
hostname: google.com
description: If your website has a favicon, it can be included in your Google Search results. Follow these favicon SEO instructions to make your site eligible.
sitename: Google for Developers
date: "2026-08-28"
---
# Define a favicon to show in search results

If your site has a favicon, it can be included in Google Search results for your site.

## Implementation

Here's how to make your site eligible for a favicon in Google Search results:

1. Create a favicon that follows the guidelines.
2. Add a `<link>` tag to the header of your home page
    with the following syntax:<link rel="icon" href="/path/to/favicon.ico"> To extract the favicon information, Google relies on the following attributes of the `link` element:Attributes `rel`Google supports the following `rel` attribute values for specifying a favicon; use
            whichever one fits your use case:`icon`The icon that represents your site, as defined in the HTML standard. `apple-touch-icon`An iOS-friendly icon that represents your site, per Apple's developer documentation. `apple-touch-icon-precomposed`An alternative icon for earlier versions of iOS, per Apple's developer documentation. `href`The URL of the favicon. The URL can be a relative path ( `/smile.ico` ) or
            absolute path (`https://example.com/smile.ico` ). The URL doesn't need to be
            hosted on your site (for example, your favicon could be hosted on a content delivery
            network (CDN)).
3. Allow time for Google to recrawl and process the new information on your home page. Remember that crawling can take anywhere from several days to several weeks, depending on how often our systems determine content needs to be refreshed. You can request indexing of your site's home page by using the URL Inspection tool.

## Guidelines

You must follow these guidelines to be eligible for a favicon in Google Search results.

- 
    Google Search only supports one favicon per site, where a *site* is defined by the
    hostname. For example,`https://www.example.com/` and`https://code.example.com/` are two different hostnames, and therefore can have two
    different favicons. However,`https://www.example.com/sub-site` is a subdirectory of
    a site, and you can only set one favicon for`https://www.example.com/` , which
    applies to the site and its subdirectories.
 **Supported** :`https://example.com` (this is a domain-level home page)
 **Supported** :`https://news.example.com` (this is a subdomain-level home page)
 **Not supported** :`https://example.com/news` (this is a subdirectory-level home page)
- Googlebot-Image must be able to crawl the favicon file and Googlebot must be able to crawl the home page; they cannot be blocked for crawling.
- To help people quickly identify your site when they scan through search results, make sure your favicon is visually representative of your website's brand.
- Your favicon must be a square (1:1 aspect ratio) that's at least 8x8px. While the minimum size requirement is 8x8px, we recommend using a favicon that's larger than 48x48px so that it looks good on various surfaces. Google Search supports the following favicon file formats: BMP, GIF, ICO, PNG, JPEG, PPM, and TIFF.
- The favicon URL must be stable (don't change the URL frequently).
- Google won't show any favicon that it deems inappropriate, including pornography or hate symbols (for example, swastikas). If this type of imagery is discovered within a favicon, Google replaces it with a default icon.

## Submit feedback about favicons in search results

If you have feedback about Google's handling of favicons in search results, fill out our favicon feedback form. Note that feedback submitted here is designed to help our teams to improve the systems in Google Search overall and doesn't guarantee it will be acted upon individually.