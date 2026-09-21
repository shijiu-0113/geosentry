---
title: https://developers.google.com/search/docs/appearance/video
url: https://developers.google.com/search/docs/appearance/video
source: developers.google.com
crawled: 2026-09-19 00:40:09
---

---
title: Video SEO Best Practices | Google Search Central | Documentation | Google for Developers
url: https://developers.google.com/search/docs/appearance/video
hostname: google.com
description: Explore video best practices, including video structured data, to help increase the likelihood that your video will be displayed in search results.
sitename: Google for Developers
date: "2009-11-05"
---
# Video SEO best practices

If you have videos on your site, following these video SEO best practices can help more people find your site through video results on Google. Videos can appear in several different places on Google, including the main search results page, Video mode, Google Images, and Discover:

Optimize your videos to appear on Google by following these best practices:

## Help Google find your videos

The technical requirements for getting your content in Google's search results applies to videos too. There are some additional requirements to making your videos eligible to be discovered, crawled, and indexed by Google Search:

- Use HTML elements commonly used for embedding videos. Google can find videos referenced by a
    `<video>` ,`<embed>` ,`<iframe>` , or`<object>` element.
- Don't use fragment identifiers to load the video, as Google Search doesn't generally support URL fragments.
- If you're using JavaScript to inject the video, make sure that it appears in the rendered HTML in the URL inspection tool.
- If you're using a media API (for example, the Media Source API), make sure the HTML video container element is still injected even if the media API call fails (in addition to providing metadata about the video). That way Google can still locate the position of the video container even if there's an issue with calling the media API.
- Don't rely on user actions (such as swiping, clicking, or typing) to load the video.

To make it easier for Google to find your videos, we recommend providing metadata about the video. We support structured data, video sitemaps, and the Open Graph protocol (OGP).

## Ensure your videos can be indexed

To be eligible for video features, a video must meet the following indexing requirements:

- The watch page must be indexed.
- The indexed watch page must be performing well in Search before its video can be considered for indexing.
- The video must be embedded on a watch page.
- The video can't be hidden behind other elements.
- The video must have a valid thumbnail that's available at a stable URL.

### Use a supported video file type

To be eligible for video features, use a supported video file type. Google can process the following video file types: 3GP, 3G2, ASF, AVI, DivX, M2V, M3U, M3U8, M4V, MKV, MOV, MP4, MPEG, OGV, QVT, RAM, RM, VOB, WebM, WMV, and XAP.

Data URLs aren't supported.

### Use stable URLs

Some CDNs use quickly expiring URLs. If the video's thumbnail URL changes too often, Google may not be able to successfully index your videos. To make sure your videos can be indexed, use a single unique and stable thumbnail URL for each video.

To make your videos eligible for specific features like key moments and video previews, make sure your video files are available at stable URLs too. This also helps Google discover and process the videos consistently, confirm they are still available, and collect signals on the videos.

  If you are concerned about bad actors (for example, hackers or spammers) accessing your content,
  you can verify Googlebot before
  displaying a stable version of your media URLs. For example, you can choose to serve the
  `contentUrl`
  property only to trusted clients like Googlebot, whereas other clients accessing your page  wouldn't
  see that field. With this setup, only trusted clients will be able to access the location of
  your video file.

### Create a dedicated watch page for each video

To be eligible for video features (including video results on the main search results page, Video mode, Key Moments, the Live Badge, and other rich formats), create a dedicated watch page for each video, if it makes sense for your business.

  A *watch page*'s main purpose is to show users a single video. The
  following pages are watch pages because watching an individual video is the main reason the user
  is visiting the page:

- A video landing page
- A TV episode video player page
- A news video watch page
- A sports highlight page
- An events clip page

These pages aren't watch pages because the video is complementary to the rest of the content on the page:

- A blog post that reviews an embedded video
- A product page with a 360 video of a product
- A video category page that lists multiple videos of equal prominence
- A movie review page with an embedded movie trailer

Make sure each watch page has a page title and description that are unique to that video. For tips, check our best practices for writing good titles and descriptions.

### Using third-party embedded players

If your website embeds videos from third-party platforms like YouTube, Vimeo, or Facebook, Google may index the video both on your web page and on the third-party platform's equivalent page. Both versions may appear in video features on Google, as long as the pages meet the video indexing criteria.

For your own watch page where you've embedded the third-party player, we still recommend that you provide structured data, and you may also include these pages in your video sitemaps. To be eligible for more video features, check with your video host to ensure they allow Google to fetch your video file.

## Which URL is which?

There are several URLs associated with a video. Here's a summary of the main ones:

| URLs related to the video |  | 
|---|---|
| **1. Watch page** | The URL of the watch page that's embedding the video. If you're using a video sitemap,           this URL is the value for the `<loc>` video sitemap tag. ```  <?xml version="1.0" encoding="UTF-8"?> <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"     xmlns:video="http://www.google.com/schemas/sitemap-video/1.1"> <url> <loc> ``` **https://example.com/videos/some_video_landing_page.html** </loc>   <video:video>   ... | 
| **2. Video player** | The URL of a specific player for the video. This is often the `src` value for           an`<iframe>` element in the HTML of the watch page: <iframe src="**https://example.com/videoplayer.php?video=123** " width="640" height="360" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe> **How to provide the URL** If you're using structured data, provide the video player URL as the value for the           `VideoObject.embedUrl` property. "embedUrl": "**https://example.com/videoplayer.php?video=123** " If you're using a video sitemap, provide the video player URL as the value for the `<video:player_loc>` tag.  <video:player_loc>**https://example.com/videoplayer.php?video=123** </video:player_loc> | 
| **3. Video file** | The URL of the video file's actual content bytes, which could be hosted on the embedding site, a CDN, or on a streaming service. In the `<object>` element, the video file's URL is the value of the`data` attribute: <object data="**https://streamserver.example.com/video/123/file.mp4** " width="400" height="300"></object> In the `<video>` element, the video file's URL is the value of the`src` attribute of the`<source>` element: <video controls width="250">   <source src="**https://streamserver.example.com/video/123/file.webm** " type="video/webm" />   <source src="**https://streamserver.example.com/video/123/file.mp4** " type="video/mp4" /> </video> In the `<embed>` element, the video file's URL is the value of the`src` attribute: <embed type="video/webm" src="**https://streamserver.example.com/video/123/file.mp4** " width="400" height="300"></embed> **How to provide the URL** If you're using structured data, provide the video file's URL as the value for the           `VideoObject.contentUrl` property. "contentUrl": "**https://streamserver.example.com/video/123/file.mp4** " If you're using a video sitemap, provide the video file's URL as the value for the           `<video:content_loc>` tag.  <video:content_loc>**https://streamserver.example.com/video/123/file.mp4** </video:content_loc> | 

### Provide a high-quality video thumbnail

To be eligible to appear in video features, a video must have a valid thumbnail image. If you allow Google to fetch your video files, Google will try to automatically generate a thumbnail for you.

However, you can influence which thumbnail is shown in video features by providing your preferred thumbnail through one of the following metadata sources:

- If you're using the `<video>` HTML element, specify the`poster` attribute.
- In a video sitemap (including mRSS), specify the `<video:thumbnail_loc>` tag (or`<media:thumbnail>` respectively).
- For structured data, specify the `thumbnailUrl`
- For OGP, specify the `og:video:image` property.

If you choose to specify multiple metadata sources (for example, specifying a thumbnail in both your sitemap and structured data), make sure you're using the same thumbnail URL per video across all metadata.

| Video thumbnail specifications |  | 
|---|---|
| **Supported thumbnail formats** | BMP, GIF, JPEG, PNG, WebP, SVG, and AVIF | 
| **Size** | Minimum 60x30 pixels, larger preferred. | 
| **Location** | The thumbnail file must be accessible by Googlebot and Googlebot Images (don't block the file with robots.txt or a login requirement). Make sure that the file is consistently available at a stable URL. | 
| **Transparency** | At least 80% of the thumbnail's pixels must have an alpha (transparency) value greater than 250. | 

### Provide consistent and unique information in your structured data

  To influence how your videos appear on Google, describe your video with
  structured data. Ensure that any
  information that you provide in structured data is consistent with the actual video content and
  other metadata you provide. Make sure to provide unique information in the `thumbnailUrl`,
  `name`, and `description` properties for each video on your site.

## Enable specific video features

### Video previews

  Google selects a few seconds from your video to display a moving preview, which can help users
  better understand what they'll find in your video. To make your videos eligible for this feature,
  allow Google to fetch your video files. You can set the maximum
  duration for these video previews using the `max-video-preview`
  robots `meta` tag.

### Key moments

The key moments feature is a way for users to navigate video segments like chapters in a book, which can help users engage more deeply with your content. Google Search tries to automatically detect the segments in your video and show key moments to users, without any effort on your part. Alternatively, you can tell Google about the important points of your video. We will prioritize key moments set by you, either through structured data or the YouTube description.

- **If your video is embedded on your web page or you're running a video platform** , there are two ways that you can enable key moments:
  - `Clip` structured data:
          Specify the exact start and end time to each segment, and what label to display for each
          segment. This is supported in all languages where Google Search is available.
  - `SeekToAction` structured data:
          Tell Google where timestamps typically go in your URL structure, so that Google can
          automatically identify key moments and link users to those points within the video. This
          is supported for the following languages: English, Spanish, Portuguese, Italian, Chinese,
          French, Japanese, German, Turkish, Korean, Dutch, and Russian.
- **If your video is hosted on YouTube** , you can specify the exact timestamps and labels
       in the video description on YouTube. Check out the
      best practices for marking timestamps in YouTube descriptions.
      This is supported in all languages where Google Search is available. If you want to enable
      Video Chapters on YouTube, follow these
        additional guidelines.

To opt out of the key moments feature completely (including any efforts Google may make to show
    key moments automatically for your video), use the
  `nosnippet` `meta` tag.
  

### Live Badge

  For livestreaming videos, you can enable a red "LIVE" badge to appear in search results by using
  `BroadcastEvent`
  structured data.

## Allow Google to fetch your video files

Google needs to successfully fetch the actual bytes of a video file to enable features like video previews and key moments.

Allow Google to find and fetch your video files by following these best practices:

- Allow Google to fetch the video's streaming file URL (such as M3U8). Don't block the URL of
    the actual video bytes with the `noindex` rule or robots.txt file.
- The video file must be available at a stable URL.
- Use structured data to provide the `contentURL` value of a supported file type.
- The host of the video watch page and the server that's streaming the actual video must have
    enough server resources to support crawling. So if your landing page at `example.com/puppies.html` has an embedded puppies video served by`streamserver.example.com` , both`example.com` and`streamserver.example.com` must meet the
    technical requirements for Google Search and
    have available server capacity.

## Remove or restrict your videos

### Remove a video

To remove a video from your site, do one of the following:

- **Return a `404 (Not found)`** for any watch page that's embedding the removed or
    expired video. In addition to the`404` response code, you can still return the HTML of the page
    to make the change transparent to most users.
- **Include a `noindex`
    robots `meta` tag** on any watch page that's embedding a
    removed or expired video. This prevents the watch page from being indexable.
- **Indicate an expiration date** in your structured data (the`expires` property) or video sitemap (use the`<video:expiration_date>` element). Here
    is an example of a video sitemap with a video that expired in November 2009:```
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
<url>
<loc>https://example.com/videos/some_video_landing_page.html</loc>
<video:video>
  <video:thumbnail_loc>
      https://example.com/thumbs/123.jpg
  </video:thumbnail_loc>
  <video:title>
      Grilling steaks for summer
  </video:title>
  <video:description>
      Bob shows you how to grill steaks perfectly every time
  </video:description>
  <video:player_loc>
      https://example.com/videoplayer?video=123
  </video:player_loc>
  
```
**<video:expiration_date>2009-11-05T19:20:30+08:00</video:expiration_date>** </video:video>
</url>
</urlset>

  When a video has an expiration date in the past, the video won't appear in video
  results. The watch page may still be shown as a text result, without a video thumbnail. This
  includes expiration dates from sitemaps, structured data, and
  `meta` tags.
  Make sure that your expiration dates are correct for each video. While this is useful if your
  video is no longer available after the expiration date, it's easy to accidentally set the date
  to the past for an available video. If a video doesn't expire, don't include expiration
  information.

### Restrict a video based on the user's location

You can restrict search results for your video based on the user's location. If your video doesn't have any country restrictions, omit the country restriction tags.

#### Restrict using structured data

  If you use `VideoObject` structured data
  to describe a video, set the
  `regionsAllowed`
  property to specify which regions can get the video result. If you omit this property, all
  regions can see the video in search results.

  Alternatively, you can use the `ineligibleRegion`
  property to specify which regions can't get the video result.

#### Restrict using a video sitemap

  In a video sitemap, the `<video:restriction>`
  tag can be used to allow or deny the video from appearing in specific countries. Only one
  `<video:restriction>` tag is allowed per video entry.

  The `<video:restriction>` tag must contain one or more space-delimited
  ISO 3166-1 two- or three-letter country codes. The
  required `relationship` attribute specifies the type of restriction.

- `relationship="allow"` : The video can appear only for the specified countries. If
    no countries are specified, the video won't appear anywhere.
- `relationship="deny"` : The video can appear everywhere except for the specified
    countries. If no countries are specified, the video will appear everywhere.

In this video sitemap example, the video will only appear in search results in Canada and Mexico.

```
<url>
  <loc>https://example.com/videos/some_video_landing_page.html</loc>
  <video:video>
    <video:thumbnail_loc>
            https://example.com/thumbs/123.jpg
    </video:thumbnail_loc>
    <video:title>Grilling steaks for summer</video:title>
    <video:description>
        Bob shows you how to get perfectly done steaks every time
    </video:description>
    <video:player_loc>
          https://example.com/player?video=123
    </video:player_loc>
    <video:restriction relationship="allow">ca mx</video:restriction>
  </video:video>
</url>
```
## Optimize for SafeSearch

SafeSearch is a setting in Google user accounts that specifies whether to show or block explicit images, videos, and websites in Google Search results. Make sure Google understands the nature of your site so that Google can apply SafeSearch filters to your site if appropriate. Learn more about labeling SafeSearch pages.

## Monitor video watch pages with Search Console

The following Search Console reports and tools can help you monitor and optimize how your video content is performing on Google Search:

- Video indexing report: See how many of your indexed watch pages contain an indexed video, and see reasons for why other videos didn't get indexed.
- Video rich result report:
    Review and fix issues with your `VideoObject` structured data implementation.
- Performance report: Use the Videos search appearance filter to monitor how your videos are performing in Google Search.

## Troubleshoot video issues

You can troubleshoot video issues with Search Console. See the video troubleshooting guide for help.