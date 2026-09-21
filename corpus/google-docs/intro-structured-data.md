---
title: Intro to How Structured Data Markup Works | Google Search Central | Documentation | Google for Developers
url: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
hostname: google.com
description: Google uses structured data markup to understand content. Explore this guide to discover how structured data works, review formats, and learn where to place it on your site.
sitename: Google for Developers
date: "2024-02-05"
---
# Introduction to structured data markup in Google Search

Google Search works hard to understand the content of a page. You can help us by providing explicit clues about the meaning of a page to Google by including structured data on the page. Structured data is a standardized format for providing information about a page and classifying the page content; for example, on a recipe page, what are the ingredients, the cooking time and temperature, the calories, and so on.

## Why add structured data to a page?

Adding structured data can enable search results that are more engaging to users and might
  encourage them to interact more with your website, which are called *rich results*.
  Here are some case studies of websites that have implemented structured data for their site:

- Rotten Tomatoes added structured data to 100,000 unique pages and measured a 25% higher click-through rate for pages enhanced with structured data, compared to pages without structured data.
- The Food Network has converted 80% of their pages to enable search features, and has seen a 35% increase in visits.
- Rakuten has found that users spend 1.5x more time on pages that implemented structured data than on non-structured data pages, and have a 3.6x higher interaction rate on AMP pages with search features vs non-feature AMP pages.
- Nestlé has measured pages that show as rich results in search have an 82% higher click through rate than non-rich result pages.

## How structured data works in Google Search

Google uses structured data that it finds on the web to understand the content of the page, as well as to gather information about the web and the world in general, such as information about the people, books, or companies that are included in the markup. For example, when a recipe page has JSON-LD structured data (describing the title of the recipe, the author of the recipe, and other details), Google Search can use that information to display a rich result for the recipe:

Because the structured data labels each individual element of the recipe, users can search for your recipe by ingredient, calorie count, cook time, and so on.

Structured data is coded using in-page markup on the page that the information applies to. The structured data on the page describes the content of that page. Don't create blank or empty pages just to hold structured data, and don't add structured data about information that is not visible to the user, even if the information is accurate. For more technical and quality guidelines, see the Structured data general guidelines.

The Rich Results Test is an easy and useful tool for validating your structured data, and in some cases, previewing a feature in Google Search. Try it out:

## Structured data vocabulary and format

This documentation describes which properties are required, recommended, or optional for structured data with special meaning to Google Search. Most Search structured data uses schema.org vocabulary, but you should rely on the Google Search Central documentation as definitive for Google Search behavior, rather than the schema.org documentation. There are more attributes and objects on schema.org that aren't required by Google Search; they may be useful for other search engines, services, tools, and platforms.

Be sure to check your structured data using the Rich Results Test during development, and the Rich result status reports after deployment, to monitor the validity of your pages, which might break after deployment due to templating or serving issues.

You must include all the required properties for an object to be eligible for appearance in
  Google Search with enhanced display. In general, defining more recommended features can make
  it more likely that your information can appear in Search results with enhanced display.
  **However**, it is more important to supply fewer but complete and accurate
  recommended properties rather than trying to provide every possible recommended property with
  less complete, badly-formed, or inaccurate data.

In addition to the properties and objects documented here, Google can make general use of the
  `sameAs` property and other
  schema.org
  structured data. Some of these elements may be used to enable future Search features, if they
  are deemed useful.

### Supported formats

Google Search supports structured data in the following formats, unless documented otherwise. In general, we recommend using a format that's easiest for you to implement and maintain (in most cases, that's JSON-LD); all 3 formats are equally fine for Google, as long as the markup is valid and properly implemented per the feature's documentation.

| Formats |  | 
|---|---|
| JSON-LD* **(Recommended)** | A JavaScript notation embedded in a `<script>` tag in the`<head>` and`<body>` elements of an HTML page. The       markup is not interleaved with the user-visible text, which makes nested data items easier       to express, such as the`Country` of a`PostalAddress` of a`MusicVenue` of an`Event` .       Also, Google can read JSON-LD data when it is dynamically       injected into the page's contents, such as by JavaScript code or embedded widgets in       your content management system. | 
| Microdata | An open-community HTML specification used to nest structured data within HTML       content. Like RDFa, it uses HTML tag attributes to name the properties you want       to expose as structured data. It is typically used in the `<body>` element, but can be used in the`<head>` element. | 
| RDFa | An HTML5 extension that supports linked data by introducing       HTML tag attributes that       correspond to the user-visible content that you want to describe for search engines. RDFa       is commonly used in both the `<head>` and`<body>` sections of the HTML page. | 

## Structured data guidelines

Be sure to follow the general structured data guidelines, as well as any guidelines specific to your structured data type; otherwise your structured data might be ineligible for rich result display in Google Search.

## Get started with structured data

If you're new to structured data, check out schema.org beginner's guide to structured data. While the guide focuses on Microdata, the basic ideas are relevant for JSON-LD and RDFa.

Once you're comfortable with the basics of structured data, explore the list of structured data features in Google Search and pick a feature to implement. Each guide goes into detail on how to implement the structured data in a way that makes your site eligible for a rich result appearance on Google Search.

## Measuring the effect of structured data

You probably want to compare performance of your pages with structured data with those pages that don't have structured data, in order to decide if it's worth your effort. The best way to do that is to run a before and after test on a few pages on your site. This can be a little tricky, since page views can vary for a single page for various reasons.

1. Take some pages on your site that are not using any structured data, and have several months of data in Search Console. Be sure to choose pages that won't be affected by the time of year or timeliness of the page content; use pages that won't change much, but are still popular enough to be read often enough to generate meaningful data.
2. Add structured data or other features to your pages. Confirm that your markup is valid, and that Google has found your structured data using the URL Inspection tool on your page.
3. Record the performance for a few months in the Performance report, and filter by URL to compare performance of your page.