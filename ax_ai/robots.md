# =========================================================================
# Robots.txt for axiomaticlab.com
# =========================================================================

User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

# Explicitly allow major AI and LLM Web Crawlers
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Google-Extended
Allow: /

# Link to your XML sitemap for traditional search engines
Sitemap: https://axiomaticlab.com
