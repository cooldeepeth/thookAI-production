"""
Seed the template marketplace with 30 curated starter templates.

Usage:
    cd backend && python scripts/seed_templates.py

Idempotent: skips if templates collection already has > 10 documents.
"""

import asyncio
import uuid
import sys
import os
from datetime import datetime, timezone

# Ensure backend/ is on the path so we can import config and database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings  # noqa: E402
from database import db      # noqa: E402


def get_seed_templates() -> list[dict]:
    """
    Return 30 curated seed templates ready for insertion into MongoDB.
    Each template mirrors the schema used in backend/routes/templates.py.
    """
    now = datetime.now(timezone.utc)

    templates = [
        # ========================================================
        # THOUGHT LEADERSHIP (8) - LinkedIn focus
        # ========================================================
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Unpopular Industry Truth",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "bold_statement",
            "hook_structure": "Most [professionals] won't tell you this about [topic]. But I will.",
            "body_structure": [
                "State the uncomfortable truth plainly",
                "Explain why the industry keeps quiet about it",
                "Share a personal experience that proved it true",
                "Offer a better mental model or framework",
                "End with what you changed as a result"
            ],
            "cta_pattern": "What's the biggest uncomfortable truth in your industry? Drop it below.",
            "example_post": (
                "Most startup advisors won't tell you this about fundraising. But I will.\n\n"
                "Raising money is not validation. I've watched 6 startups in my portfolio "
                "raise $2M+ seed rounds and die within 18 months.\n\n"
                "The industry celebrates fundraising announcements like they're wins. "
                "They aren't. They're obligations.\n\n"
                "Here's what I learned after 10 years:\n"
                "- Revenue is validation\n"
                "- Retention is validation\n"
                "- A term sheet is a starting line, not a finish line\n\n"
                "I now tell every founder I advise: delay fundraising as long as possible. "
                "Build proof first.\n\n"
                "What's the biggest uncomfortable truth in your industry? Drop it below."
            ),
            "content_pillars": ["leadership", "industry_insights", "transparency"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Lessons From Leading a Team Through Crisis",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "story_opening",
            "hook_structure": "Last [time period], my team went through [crisis]. Here's what it taught me about leadership.",
            "body_structure": [
                "Set the scene - what happened",
                "Describe the initial reaction and mistakes",
                "Share the turning-point decision",
                "List 3 leadership principles you discovered",
                "Reflect on how it changed your approach permanently"
            ],
            "cta_pattern": "What's the toughest leadership moment you've navigated? I'd love to hear your story.",
            "example_post": (
                "Last quarter, my team lost our biggest client overnight. "
                "Here's what it taught me about leadership.\n\n"
                "Day one: panic. I made every wrong move. Closed my office door. "
                "Tried to solve it alone. Sent a vague Slack message saying 'we'll be fine.'\n\n"
                "Day two: I swallowed my pride and held an all-hands.\n\n"
                "I told the team exactly where we stood. Revenue gap. Runway impact. "
                "What I didn't know yet.\n\n"
                "What happened next blew me away:\n"
                "- Three team members pitched new revenue ideas by EOD\n"
                "- Our junior dev proposed a product pivot that landed 2 new clients\n"
                "- Morale actually went UP because people felt trusted\n\n"
                "Leadership lesson: transparency isn't weakness. It's your biggest multiplier.\n\n"
                "What's the toughest leadership moment you've navigated? I'd love to hear your story."
            ),
            "content_pillars": ["leadership", "resilience", "team_management"],
            "format_type": "story",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Framework That Changed My Decision-Making",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "bold_statement",
            "hook_structure": "I used to spend weeks making decisions. Then I learned the [framework name]. Now it takes me [time].",
            "body_structure": [
                "Describe the old way you made decisions and why it was broken",
                "Introduce the framework with a clear name",
                "Break the framework into 3-4 steps",
                "Give a concrete example of applying it",
                "Share the result and time saved"
            ],
            "cta_pattern": "Save this for next time you're stuck on a tough decision.",
            "example_post": (
                "I used to spend weeks making decisions. Then I learned the 10/10/10 Rule. "
                "Now it takes me 10 minutes.\n\n"
                "Here's how it works:\n\n"
                "Ask yourself 3 questions before any big decision:\n"
                "1. How will I feel about this in 10 minutes?\n"
                "2. How will I feel about this in 10 months?\n"
                "3. How will I feel about this in 10 years?\n\n"
                "Example: I was offered a VP role at a Fortune 500. Great salary. Safe path.\n\n"
                "- 10 minutes: Excited\n"
                "- 10 months: Comfortable but restless\n"
                "- 10 years: Regretful I didn't build something of my own\n\n"
                "I turned it down and started my company. Best decision I've ever made.\n\n"
                "Save this for next time you're stuck on a tough decision."
            ),
            "content_pillars": ["productivity", "frameworks", "decision_making"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Data-Backed Industry Prediction",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "data_point",
            "hook_structure": "[Stat or data point] just hit [milestone]. Here's why that changes everything for [industry].",
            "body_structure": [
                "Present the data point and its source",
                "Explain why most people are interpreting it wrong",
                "Share your contrarian interpretation",
                "Predict 2-3 downstream effects",
                "Advise what smart professionals should do now"
            ],
            "cta_pattern": "Agree or disagree? I want to hear your prediction in the comments.",
            "example_post": (
                "AI-generated content now accounts for 15% of all new web pages indexed by Google. "
                "Here's why that changes everything for marketers.\n\n"
                "Most people see this and think: 'Content is dead. AI wins.'\n\n"
                "I see the opposite.\n\n"
                "When 15% of content is generic AI output, the remaining 85% that carries "
                "real insight, personal experience, and original data becomes exponentially "
                "more valuable.\n\n"
                "My predictions:\n"
                "1. Google will increasingly reward E-E-A-T signals (experience, expertise)\n"
                "2. Brands that invest in original research will dominate organic search by 2026\n"
                "3. 'Thought leadership' will shift from buzzword to survival strategy\n\n"
                "What smart marketers should do NOW:\n"
                "- Build a proprietary data moat\n"
                "- Document real experiences, not regurgitated tips\n"
                "- Use AI to scale distribution, not creation\n\n"
                "Agree or disagree? I want to hear your prediction in the comments."
            ),
            "content_pillars": ["industry_trends", "data", "predictions"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Career Advice I Wish I Got Earlier",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "bold_statement",
            "hook_structure": "I'm [age/years into career]. Here are [N] things I wish someone told me at [earlier age/stage].",
            "body_structure": [
                "Set up your credibility and timeline",
                "List 5-7 career truths as short punchy statements",
                "Add a one-line explanation under each",
                "End with the one that had the biggest impact",
                "Invite others to add theirs"
            ],
            "cta_pattern": "What's the one piece of career advice you'd give your younger self?",
            "example_post": (
                "I'm 15 years into my career. Here are 7 things I wish someone told me at 25.\n\n"
                "1. Your network is not your LinkedIn connections.\n"
                "It's the 10 people who'd take your call at midnight.\n\n"
                "2. Titles are vanity metrics.\n"
                "Impact is the only resume that matters.\n\n"
                "3. Saying no is a superpower.\n"
                "Every yes to the wrong thing is a no to the right one.\n\n"
                "4. The best career move is often lateral.\n"
                "Breadth beats depth until you find your thing.\n\n"
                "5. Nobody cares about your career plan.\n"
                "They care about what problems you solve.\n\n"
                "6. Mentors don't fall from the sky.\n"
                "You earn them by being worth mentoring.\n\n"
                "7. Rest is productive.\n"
                "Burnout has a 6-month recovery tax.\n\n"
                "The one that changed everything? #3. Learning to say no freed me to build "
                "the career I actually wanted.\n\n"
                "What's the one piece of career advice you'd give your younger self?"
            ),
            "content_pillars": ["career", "self_improvement", "wisdom"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Hiring Mistake That Taught Me Everything",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "story_opening",
            "hook_structure": "I hired [number] people last year. The biggest mistake I made taught me more than every good hire combined.",
            "body_structure": [
                "Open with the hiring context",
                "Describe the mistake without blaming the person",
                "Identify the root cause (your process, not the candidate)",
                "Share the new hiring principle you adopted",
                "Show the before/after results"
            ],
            "cta_pattern": "What hiring lesson did you learn the hard way? Share below.",
            "example_post": (
                "I hired 12 people last year. The biggest mistake I made taught me more "
                "than every good hire combined.\n\n"
                "I hired a senior engineer with a flawless resume. FAANG pedigree. "
                "Crushed every technical interview.\n\n"
                "Within 60 days, 3 team members asked to transfer.\n\n"
                "The problem wasn't skill. It was values alignment. They were brilliant "
                "but fundamentally disagreed with how we build (collaborative, messy, iterative).\n\n"
                "My mistake: I optimized for capability and ignored compatibility.\n\n"
                "New hiring rule: skills can be taught in months. Values alignment takes years "
                "to change, if ever.\n\n"
                "Now our interview process:\n"
                "- 40% values and working-style questions\n"
                "- 30% skills assessment\n"
                "- 30% real scenario collaboration\n\n"
                "Result: retention went from 70% to 94% in one year.\n\n"
                "What hiring lesson did you learn the hard way? Share below."
            ),
            "content_pillars": ["hiring", "leadership", "team_building"],
            "format_type": "story",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Meeting I'll Never Forget",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "story_opening",
            "hook_structure": "A [person] once told me something in a meeting that I've thought about every day since.",
            "body_structure": [
                "Set the scene - who, where, what meeting",
                "Build tension - what was being discussed",
                "Deliver the pivotal quote or moment",
                "Explain why it shifted your perspective",
                "Connect it to a universal leadership or career lesson"
            ],
            "cta_pattern": "Has someone ever said something to you that completely shifted your perspective? Tell me about it.",
            "example_post": (
                "A board member once told me something in a meeting that I've thought about "
                "every day since.\n\n"
                "We were reviewing Q3 numbers. Growth was solid. Team was executing. "
                "I was feeling confident.\n\n"
                "Then she leaned forward and asked:\n\n"
                "'You're growing. But are you building something that would survive '  "
                "'without you for 6 months?'\n\n"
                "Silence. I had no answer.\n\n"
                "That question exposed my biggest blind spot: I was the bottleneck I couldn't see.\n\n"
                "Within 3 months I:\n"
                "- Documented every decision process I owned\n"
                "- Promoted 2 team leads to own their domains completely\n"
                "- Took a 2-week disconnect vacation (the company didn't skip a beat)\n\n"
                "The best leaders build systems, not dependencies.\n\n"
                "Has someone ever said something to you that completely shifted your perspective? "
                "Tell me about it."
            ),
            "content_pillars": ["leadership", "self_awareness", "growth"],
            "format_type": "story",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "What I Stopped Doing to 10x My Results",
            "category": "thought_leadership",
            "platform": "linkedin",
            "hook_type": "bold_statement",
            "hook_structure": "I didn't 10x my [results] by doing more. I did it by stopping these [N] things.",
            "body_structure": [
                "Open with the counterintuitive result",
                "List 4-5 things you stopped doing",
                "For each, explain why it felt productive but wasn't",
                "Share the replacement habit or approach",
                "Summarize the overall mindset shift"
            ],
            "cta_pattern": "What's one thing you stopped doing that made everything better?",
            "example_post": (
                "I didn't 10x my revenue by doing more. I did it by stopping these 5 things.\n\n"
                "1. Stopped attending every meeting.\n"
                "If I'm not deciding or contributing, I decline. Freed 12 hours/week.\n\n"
                "2. Stopped chasing every lead.\n"
                "Built an ideal client scorecard. Now I only pursue 8/10+ fits.\n\n"
                "3. Stopped writing proposals from scratch.\n"
                "Templatized 80% of it. Customized only the strategic section.\n\n"
                "4. Stopped checking email before 11am.\n"
                "Morning hours are for deep work. Everything else can wait.\n\n"
                "5. Stopped saying 'I'll think about it.'\n"
                "Now it's yes or no within 24 hours. Decision fatigue was killing me.\n\n"
                "The mindset shift: productivity isn't about adding. It's about subtracting "
                "everything that doesn't compound.\n\n"
                "What's one thing you stopped doing that made everything better?"
            ),
            "content_pillars": ["productivity", "mindset", "efficiency"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },

        # ========================================================
        # STORYTELLING (6) - LinkedIn + Instagram
        # ========================================================
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Rejection That Redirected My Life",
            "category": "storytelling",
            "platform": "linkedin",
            "hook_type": "story_opening",
            "hook_structure": "In [year], I was rejected from [thing]. It was the best thing that ever happened to me.",
            "body_structure": [
                "Open with the rejection moment - make it vivid",
                "Describe the emotional fallout",
                "Explain what you did next (the pivot)",
                "Show where that pivot led you",
                "Deliver the insight: rejection as redirection"
            ],
            "cta_pattern": "What rejection turned out to be the best thing that happened to you?",
            "example_post": (
                "In 2019, I was rejected from Y Combinator. It was the best thing that "
                "ever happened to me.\n\n"
                "I remember sitting in my car outside a coffee shop, reading the email. "
                "'We've decided not to move forward.'\n\n"
                "I felt like a fraud. I'd told everyone I was going to get in.\n\n"
                "But that rejection forced me to do something I'd been avoiding: actually "
                "talk to customers.\n\n"
                "Without the YC safety net, I had to sell before I could build. "
                "I cold-called 200 companies in 3 months.\n\n"
                "What I learned:\n"
                "- Our original idea was solving a problem nobody had\n"
                "- The real pain point was 3 layers deeper\n"
                "- Revenue validation > accelerator validation\n\n"
                "Today that 'failed' startup does $4M ARR. Without the rejection, "
                "I'd have built the wrong product with fancy credentials.\n\n"
                "What rejection turned out to be the best thing that happened to you?"
            ),
            "content_pillars": ["resilience", "entrepreneurship", "personal_growth"],
            "format_type": "story",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Conversation That Changed Everything",
            "category": "storytelling",
            "platform": "linkedin",
            "hook_type": "story_opening",
            "hook_structure": "A [stranger/mentor/client] told me something [time ago] that completely changed how I [do X].",
            "body_structure": [
                "Set the scene and context",
                "Quote the exact words they said",
                "Describe your initial reaction (disbelief, resistance)",
                "Show how you tested their advice",
                "Reveal the transformation it created"
            ],
            "cta_pattern": "What's the most powerful piece of advice you've received from an unexpected source?",
            "example_post": (
                "A taxi driver in Mumbai told me something 3 years ago that completely "
                "changed how I run my business.\n\n"
                "I was venting about work stress during a ride to the airport. "
                "Complaining about how I couldn't find good people.\n\n"
                "He looked at me in the rearview mirror and said:\n\n"
                "'Sir, if everyone around you is the problem, the problem is probably you.'\n\n"
                "I laughed it off. But on the 4-hour flight home, I couldn't stop "
                "thinking about it.\n\n"
                "He was right.\n\n"
                "I wasn't a bad leader because of bad employees. I was:\n"
                "- Hiring based on resumes, not values\n"
                "- Micromanaging because I didn't trust my own hiring\n"
                "- Creating a culture where good people didn't want to stay\n\n"
                "I overhauled everything. New hiring process. New management style. "
                "New level of self-awareness.\n\n"
                "Turnover dropped 60% in one year.\n\n"
                "Sometimes the best advice comes from the least expected places.\n\n"
                "What's the most powerful piece of advice you've received from an unexpected source?"
            ),
            "content_pillars": ["self_awareness", "leadership", "humility"],
            "format_type": "story",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "My Biggest Professional Failure",
            "category": "storytelling",
            "platform": "instagram",
            "hook_type": "story_opening",
            "hook_structure": "I don't talk about this often, but [time ago] I [failed at X]. Here's the full story.",
            "body_structure": [
                "Open with vulnerability - the failure moment",
                "Give context: what you were trying to achieve",
                "Walk through what went wrong step by step",
                "Share the rock-bottom moment",
                "End with what you rebuilt and the lesson"
            ],
            "cta_pattern": "Double tap if you've learned more from failure than success. What's your biggest lesson?",
            "example_post": (
                "I don't talk about this often, but 4 years ago I ran a company "
                "into the ground. Here's the full story.\n\n"
                "We had 15 employees, $80K MRR, and growing fast. I thought we were "
                "unstoppable.\n\n"
                "What went wrong:\n"
                "- I hired ahead of revenue (classic)\n"
                "- I ignored churn signals because new sales covered them\n"
                "- I said yes to every feature request instead of focusing\n\n"
                "By month 18, we were burning $120K/month with $60K coming in.\n\n"
                "I had to lay off 11 people in a single week. I'll never forget those "
                "conversations.\n\n"
                "Rock bottom was sitting alone in an empty office at 2am wondering "
                "if I was cut out for this.\n\n"
                "But here's what failure taught me:\n"
                "- Cash flow is oxygen. Revenue means nothing if it's leaking out faster.\n"
                "- Focus beats ambition every single time.\n"
                "- The best time to fix culture is when things are good, not when they're breaking.\n\n"
                "Today I run a profitable business with half the team and 3x the focus.\n\n"
                "Double tap if you've learned more from failure than success. "
                "What's your biggest lesson?"
            ),
            "content_pillars": ["vulnerability", "entrepreneurship", "lessons_learned"],
            "format_type": "carousel_caption",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Day in the Life: Building in Public",
            "category": "storytelling",
            "platform": "instagram",
            "hook_type": "story_opening",
            "hook_structure": "What a day of building a [business/product] actually looks like. No filter.",
            "body_structure": [
                "Open with the morning routine (honest, not glamorous)",
                "Share the hardest moment of the day",
                "Include a small win or breakthrough",
                "Show the unglamorous work (emails, bugs, calls)",
                "Close with an honest reflection on the day"
            ],
            "cta_pattern": "Share your real day-in-the-life below. I want to hear the unfiltered version.",
            "example_post": (
                "What a day of building a startup actually looks like. No filter.\n\n"
                "6:30am - Alarm. Didn't sleep well because I realized our pricing page "
                "has a bug that's been live for 3 days.\n\n"
                "7:00am - Fixed the bug before coffee. Tested on 4 browsers. "
                "Probably should write tests. Added it to the 'someday' list.\n\n"
                "9:00am - Sales call with a potential client. They loved the demo. "
                "Then asked for 6 custom features. I said no to 5 of them.\n\n"
                "11:00am - Team standup. Our designer is stuck on the onboarding flow. "
                "Spent an hour whiteboarding together.\n\n"
                "1:00pm - Lunch at my desk. Reviewed metrics. Churn ticked up 0.3%. "
                "Sent 5 personal emails to churned users asking why.\n\n"
                "3:00pm - Investor update email. Took 2 hours to write 300 words. "
                "Transparency is hard when numbers are mixed.\n\n"
                "6:00pm - Small win: one of the churned users replied and re-subscribed "
                "after I solved their issue personally.\n\n"
                "8:00pm - Closed laptop. The glamorous founder life: "
                "90% unglamorous work, 10% moments that make it worth it.\n\n"
                "Share your real day-in-the-life below. I want to hear the unfiltered version."
            ),
            "content_pillars": ["building_in_public", "authenticity", "startup_life"],
            "format_type": "carousel_caption",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Client Who Taught Me More Than Any Course",
            "category": "storytelling",
            "platform": "linkedin",
            "hook_type": "story_opening",
            "hook_structure": "My most difficult client taught me more in [time] than [years] of [education/experience].",
            "body_structure": [
                "Introduce the client situation (anonymized)",
                "Describe the challenge or conflict",
                "Share what you tried first (and why it failed)",
                "Reveal the breakthrough approach",
                "Extract the transferable professional lesson"
            ],
            "cta_pattern": "Who taught you the most in your career - and were they easy to work with?",
            "example_post": (
                "My most difficult client taught me more in 6 months than 4 years of business school.\n\n"
                "They challenged every recommendation. Questioned every invoice. "
                "Pushed back on timelines constantly.\n\n"
                "At first, I was frustrated. I almost fired them.\n\n"
                "Then I realized something: they weren't being difficult. "
                "They were being rigorous.\n\n"
                "What I tried first: defending my work harder. Sending longer proposals. "
                "Adding more data.\n\n"
                "What actually worked: I started asking 'Why do you push back on this?' "
                "instead of defending.\n\n"
                "Their answers revealed blind spots in my process I'd never seen:\n"
                "- I was presenting solutions before fully understanding their constraints\n"
                "- My timelines assumed perfect conditions (they never are)\n"
                "- I was solving the problem I wanted to solve, not theirs\n\n"
                "That client renewed for 3 more years. And every client since has benefited "
                "from what they taught me.\n\n"
                "Who taught you the most in your career - and were they easy to work with?"
            ),
            "content_pillars": ["client_relationships", "growth", "professional_development"],
            "format_type": "story",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "From Zero to First Dollar Online",
            "category": "storytelling",
            "platform": "instagram",
            "hook_type": "story_opening",
            "hook_structure": "I still remember the day I made my first $[amount] online. Here's how it happened.",
            "body_structure": [
                "The moment you earned your first dollar (make it vivid)",
                "Rewind - what your life looked like before",
                "The journey: attempts that failed first",
                "The specific thing that finally worked",
                "What that first dollar meant and where it led"
            ],
            "cta_pattern": "Do you remember your first dollar moment? Tell me your story.",
            "example_post": (
                "I still remember the day I made my first $47 online. Here's how it happened.\n\n"
                "It was a Tuesday at 11pm. I was eating ramen in a studio apartment. "
                "My phone buzzed: 'You've received a payment.'\n\n"
                "I screamed. My neighbor knocked on the wall.\n\n"
                "Rewind 8 months. I had:\n"
                "- Started 3 blogs (all abandoned)\n"
                "- Tried dropshipping (lost $200 on ads)\n"
                "- Applied to 50 freelance gigs (2 replies, 0 hires)\n\n"
                "What finally worked: I stopped trying to build a 'business' and started "
                "solving one person's problem.\n\n"
                "I saw someone in a Facebook group asking for help with their Shopify theme. "
                "I knew basic CSS. I offered to help for $47.\n\n"
                "They said yes. I spent 3 hours on it. Delivered it that night.\n\n"
                "That $47 was worth more than any paycheck I'd ever received. "
                "Not because of the money, but because of the proof:\n\n"
                "Someone on the internet will pay you to solve their problem.\n\n"
                "That realization became a freelance business, then an agency, "
                "then the company I run today.\n\n"
                "Do you remember your first dollar moment? Tell me your story."
            ),
            "content_pillars": ["entrepreneurship", "origin_story", "motivation"],
            "format_type": "carousel_caption",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },

        # ========================================================
        # HOW-TO (5) - LinkedIn + X
        # ========================================================
        {
            "template_id": str(uuid.uuid4()),
            "title": "Step-by-Step Process Breakdown",
            "category": "how_to",
            "platform": "linkedin",
            "hook_type": "bold_statement",
            "hook_structure": "I [achieved result] in [timeframe]. Here's the exact [N]-step process I used.",
            "body_structure": [
                "State the result and timeframe for credibility",
                "Step 1: the foundation most people skip",
                "Step 2-4: the core process with specifics",
                "Step 5: the optimization that made the difference",
                "Summarize with a 'start here' call to action"
            ],
            "cta_pattern": "Bookmark this for later. Which step are you going to try first?",
            "example_post": (
                "I grew my LinkedIn following from 500 to 25,000 in 6 months. "
                "Here's the exact 5-step process I used.\n\n"
                "Step 1: Audit your profile (most people skip this)\n"
                "- Changed my headline from job title to value proposition\n"
                "- Rewrote my About section as a story, not a resume\n"
                "- Added a banner with a clear CTA\n\n"
                "Step 2: Find your content pillars\n"
                "- Picked 3 topics I could talk about for 100 posts each\n"
                "- Mine: leadership, hiring, and building in public\n\n"
                "Step 3: Post consistently (not constantly)\n"
                "- 4 posts per week, Mon/Tue/Thu/Fri at 8am\n"
                "- Quality over quantity, always\n\n"
                "Step 4: Engage before you post\n"
                "- Spent 15 min commenting on others' posts before publishing mine\n"
                "- Genuine comments, not 'Great post!'\n\n"
                "Step 5: Analyze and double down\n"
                "- Tracked which post types got the most engagement\n"
                "- Personal stories outperformed tips 3:1\n"
                "- Doubled down on storytelling\n\n"
                "Bookmark this for later. Which step are you going to try first?"
            ),
            "content_pillars": ["social_media", "growth", "personal_branding"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Quick Tactical Thread: How to Do X",
            "category": "how_to",
            "platform": "x",
            "hook_type": "bold_statement",
            "hook_structure": "Most people overcomplicate [task]. Here's how to do it in [time/steps]:",
            "body_structure": [
                "Tweet 1: Hook + promise",
                "Tweets 2-5: One tactical step per tweet with specifics",
                "Tweet 6: Common mistakes to avoid",
                "Tweet 7: Recap + CTA to bookmark"
            ],
            "cta_pattern": "Repost this thread if it was helpful. Follow me for more tactical breakdowns.",
            "example_post": (
                "Most people overcomplicate cold outreach. Here's how to book 10 "
                "meetings per week in 4 steps:\n\n"
                "Step 1: Build a targeted list of 50 prospects.\n"
                "Use LinkedIn Sales Nav. Filter by role, company size, and industry. "
                "Quality > quantity.\n\n"
                "Step 2: Research 3 things per prospect.\n"
                "Recent post, company news, shared connection. This takes 2 min per person.\n\n"
                "Step 3: Send a 3-line email.\n"
                "Line 1: What you noticed about them\n"
                "Line 2: How you've helped similar companies\n"
                "Line 3: 'Worth a 15-min chat?'\n\n"
                "Step 4: Follow up on Day 3 and Day 7.\n"
                "Add new value each time. Never say 'just following up.'\n\n"
                "Common mistakes:\n"
                "- Sending 500 generic emails (0.1% reply rate)\n"
                "- Leading with your product instead of their problem\n"
                "- Giving up after one email (80% of meetings come from follow-ups)\n\n"
                "TL;DR: 50 researched prospects > 500 spray-and-pray emails.\n\n"
                "Repost this thread if it was helpful. Follow me for more tactical breakdowns."
            ),
            "content_pillars": ["sales", "outreach", "tactics"],
            "format_type": "thread",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Beginner's Mistake Fix",
            "category": "how_to",
            "platform": "x",
            "hook_type": "question",
            "hook_structure": "Why does your [thing] underperform? You're probably making these [N] mistakes:",
            "body_structure": [
                "Tweet 1: Hook question that resonates",
                "Tweets 2-4: One mistake per tweet + the fix",
                "Tweet 5: The mindset shift behind all these fixes",
                "Tweet 6: CTA to save/follow"
            ],
            "cta_pattern": "Save this. You'll need it. Follow @handle for more breakdowns like this.",
            "example_post": (
                "Why does your content underperform? You're probably making these 4 mistakes:\n\n"
                "Mistake 1: Writing for everyone.\n"
                "Fix: Pick ONE reader persona. Write as if you're emailing them directly. "
                "Specificity wins.\n\n"
                "Mistake 2: Burying the hook.\n"
                "Fix: Your first line should stop the scroll. Lead with the most surprising, "
                "emotional, or useful part.\n\n"
                "Mistake 3: No clear structure.\n"
                "Fix: Use whitespace. Use bullets. Use numbers. Wall-of-text posts die.\n\n"
                "Mistake 4: No CTA.\n"
                "Fix: Every post should ask one thing: comment, share, follow, or save. "
                "Don't leave engagement to chance.\n\n"
                "The mindset shift: You're not a content creator. You're an attention architect. "
                "Every element of your post should earn the next second of attention.\n\n"
                "Save this. You'll need it."
            ),
            "content_pillars": ["content_creation", "marketing", "writing"],
            "format_type": "thread",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Tool Stack Breakdown",
            "category": "how_to",
            "platform": "linkedin",
            "hook_type": "bold_statement",
            "hook_structure": "I run a [type of business] with only [N] tools. Here's my entire stack and why I chose each one.",
            "body_structure": [
                "State the business context and the constraint (few tools)",
                "List each tool with a one-line 'why'",
                "Highlight the one tool you'd keep if you could only have one",
                "Share what you tried and dropped (and why)",
                "End with a principle: simplicity over feature bloat"
            ],
            "cta_pattern": "What's the one tool you can't live without? Drop it in the comments.",
            "example_post": (
                "I run a 7-figure consulting business with only 6 tools. "
                "Here's my entire stack and why I chose each one.\n\n"
                "1. Notion - CRM, project management, SOPs, client portal. "
                "It replaced 4 separate tools.\n\n"
                "2. Loom - Client updates, async meetings, onboarding videos. "
                "Saves 5+ hours/week on calls.\n\n"
                "3. Stripe - Billing, invoicing, subscription management. "
                "Set it and forget it.\n\n"
                "4. Slack - Team comms and client channels. "
                "One tool for all conversations.\n\n"
                "5. Figma - Proposals, presentations, deliverables. "
                "Way more flexible than PowerPoint.\n\n"
                "6. Cal.com - Scheduling. Open source, no subscription fees.\n\n"
                "If I could only keep one: Notion. It's the brain of the entire operation.\n\n"
                "What I dropped:\n"
                "- HubSpot (overkill for our size)\n"
                "- Monday.com (too many features we didn't use)\n"
                "- Google Docs (Notion does it better for collaboration)\n\n"
                "Principle: every tool should save more time than it costs to manage.\n\n"
                "What's the one tool you can't live without? Drop it in the comments."
            ),
            "content_pillars": ["tools", "productivity", "business_operations"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Before and After Transformation",
            "category": "how_to",
            "platform": "linkedin",
            "hook_type": "bold_statement",
            "hook_structure": "[N months] ago, my [metric] was [bad number]. Today it's [good number]. Here's exactly what changed.",
            "body_structure": [
                "Show the before state with specific numbers",
                "Identify the root cause of the problem",
                "Walk through the 3-4 changes you made in order",
                "Show the after state with specific numbers",
                "Give the reader a first step they can take today"
            ],
            "cta_pattern": "If this helped, repost it for someone who needs it. Follow for more tactical content.",
            "example_post": (
                "6 months ago, my email open rate was 12%. Today it's 47%. "
                "Here's exactly what changed.\n\n"
                "The before: 5,000 subscribers. 12% open rate. 0.8% click rate. "
                "I was ready to give up on email.\n\n"
                "Root cause: I was writing emails like a newsletter. "
                "Nobody wants another newsletter.\n\n"
                "Change 1: Rewrote every subject line as a personal message.\n"
                "Before: 'ThookAI Weekly Digest #47'\n"
                "After: 'I made a mistake this week - here's what I learned'\n\n"
                "Change 2: Cut email length from 800 words to 200 words.\n"
                "One idea. One story. One link.\n\n"
                "Change 3: Sent at 7am Tuesday and Thursday instead of 'whenever.'\n"
                "Consistency > optimization.\n\n"
                "Change 4: Cleaned my list. Removed 2,000 inactive subscribers.\n"
                "Smaller list, better deliverability, higher engagement.\n\n"
                "The after: 3,000 subscribers. 47% open rate. 8.2% click rate.\n\n"
                "First step you can take today: rewrite your next subject line "
                "as something you'd text to a friend.\n\n"
                "If this helped, repost it for someone who needs it."
            ),
            "content_pillars": ["email_marketing", "growth", "tactics"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },

        # ========================================================
        # CONTRARIAN (4) - X + LinkedIn
        # ========================================================
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Popular Advice That's Wrong",
            "category": "contrarian",
            "platform": "x",
            "hook_type": "contrarian_take",
            "hook_structure": "Everyone says '[popular advice].' This is terrible advice. Here's why:",
            "body_structure": [
                "State the popular advice clearly",
                "Explain why it sounds right on the surface",
                "Give 2-3 reasons it's actually harmful",
                "Share what works better (with evidence)",
                "Acknowledge the nuance - when the popular advice IS right"
            ],
            "cta_pattern": "Agree or disagree? Quote tweet with your take.",
            "example_post": (
                "Everyone says 'just ship it, you can improve later.' "
                "This is terrible advice. Here's why:\n\n"
                "It sounds right because speed matters. And iteration is real.\n\n"
                "But here's what actually happens when you ship garbage:\n\n"
                "1. First impressions are permanent. Users who try your broken V1 "
                "rarely come back for V2.\n\n"
                "2. You accumulate tech debt faster than you can pay it off. "
                "Now you're iterating on a broken foundation.\n\n"
                "3. Your team learns that quality doesn't matter. "
                "That culture is almost impossible to reverse.\n\n"
                "What works better: Ship fast, but ship COMPLETE.\n"
                "Build less scope but make it bulletproof. "
                "A perfect feature beats 10 broken ones.\n\n"
                "The nuance: 'just ship it' IS right when you're validating demand. "
                "Landing pages, mockups, waitlists - ship those immediately. "
                "But when real users touch real product? Quality is speed.\n\n"
                "Agree or disagree? Quote tweet with your take."
            ),
            "content_pillars": ["product_development", "quality", "contrarian"],
            "format_type": "thread",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Overrated vs. Underrated List",
            "category": "contrarian",
            "platform": "x",
            "hook_type": "contrarian_take",
            "hook_structure": "Overrated vs. underrated in [industry/field]. (This will upset some people.)",
            "body_structure": [
                "Open with the framing (overrated vs underrated)",
                "List 4-5 overrated things with brief reasoning",
                "List 4-5 underrated things with brief reasoning",
                "End with a thought-provoking closer"
            ],
            "cta_pattern": "What would you add to either list? Reply with yours.",
            "example_post": (
                "Overrated vs. underrated in the startup world. "
                "(This will upset some people.)\n\n"
                "OVERRATED:\n"
                "- Fundraising announcements\n"
                "- 'Move fast and break things'\n"
                "- Growth at all costs\n"
                "- Co-working spaces with beer taps\n"
                "- Vanity metrics on your pitch deck\n\n"
                "UNDERRATED:\n"
                "- Profitability from day one\n"
                "- Boring businesses that print cash\n"
                "- Taking a salary as a founder\n"
                "- Saying no to 90% of opportunities\n"
                "- Sleeping 8 hours\n\n"
                "The meta-lesson: the startup ecosystem celebrates theater. "
                "The best founders ignore the theater and focus on substance.\n\n"
                "What would you add to either list? Reply with yours."
            ),
            "content_pillars": ["startups", "contrarian", "industry_insights"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Uncomfortable Truth About Success",
            "category": "contrarian",
            "platform": "linkedin",
            "hook_type": "contrarian_take",
            "hook_structure": "Unpopular opinion: [common success metric] is actually a sign of [negative thing].",
            "body_structure": [
                "State the unpopular opinion boldly",
                "Acknowledge why people pursue this metric",
                "Present evidence for why it's misleading",
                "Offer an alternative metric that actually matters",
                "Close with a self-reflection prompt"
            ],
            "cta_pattern": "What 'success metric' are you chasing that might not actually matter? Be honest.",
            "example_post": (
                "Unpopular opinion: Being 'always busy' is actually a sign of poor prioritization.\n\n"
                "I get it. Busy feels productive. A packed calendar feels important. "
                "Telling people 'I'm so busy' feels like a badge of honor.\n\n"
                "But here's the evidence:\n\n"
                "The most effective leaders I know have MORE free time, not less.\n\n"
                "Why? Because they've:\n"
                "- Built systems that don't need them in the loop\n"
                "- Said no to everything that isn't a 'hell yes'\n"
                "- Delegated 80% of what they used to do themselves\n"
                "- Blocked 'thinking time' on their calendar (and protected it)\n\n"
                "The metric that actually matters isn't hours worked. "
                "It's decisions made per hour that moved the needle.\n\n"
                "I tracked mine for a month. The result was humbling: "
                "out of 50 hours of 'work' per week, only 8 hours produced meaningful output.\n\n"
                "Now I optimize for those 8 hours. The rest I'm trying to eliminate.\n\n"
                "What 'success metric' are you chasing that might not actually matter? Be honest."
            ),
            "content_pillars": ["productivity", "contrarian", "self_improvement"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Why I Stopped Following Best Practices",
            "category": "contrarian",
            "platform": "linkedin",
            "hook_type": "contrarian_take",
            "hook_structure": "I stopped following '[best practice]' 2 years ago. My results have never been better.",
            "body_structure": [
                "Name the best practice you abandoned",
                "Share your results before vs. after",
                "Explain what you replaced it with",
                "Why the best practice works for some but not you",
                "The principle: test everything, keep only what works for YOUR context"
            ],
            "cta_pattern": "What 'best practice' have you broken that actually improved your results?",
            "example_post": (
                "I stopped following 'post every day on social media' 2 years ago. "
                "My results have never been better.\n\n"
                "Before: 7 posts/week. Avg 40 likes. Felt like a content treadmill. "
                "I was burning out and my content showed it.\n\n"
                "After: 3 posts/week. Avg 350 likes. More DMs. Actual business leads.\n\n"
                "What I replaced it with:\n"
                "- Spending 2x more time on research per post\n"
                "- Only posting when I had something genuinely useful to say\n"
                "- Investing the saved time in commenting on others' posts\n\n"
                "Why daily posting works for some:\n"
                "- If you're building from zero, volume helps you find your voice\n"
                "- Some platforms reward frequency (early TikTok, early LinkedIn)\n"
                "- Some people genuinely have daily-quality ideas\n\n"
                "But if you're past the experimentation phase, quality compounds "
                "faster than quantity.\n\n"
                "The principle: best practices are starting points, not finish lines. "
                "Test everything. Keep only what works for YOUR context.\n\n"
                "What 'best practice' have you broken that actually improved your results?"
            ),
            "content_pillars": ["content_strategy", "contrarian", "personal_branding"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },

        # ========================================================
        # BEHIND THE SCENES (4) - Instagram + LinkedIn
        # ========================================================
        {
            "template_id": str(uuid.uuid4()),
            "title": "Revenue Transparency Report",
            "category": "behind_the_scenes",
            "platform": "linkedin",
            "hook_type": "data_point",
            "hook_structure": "Here are our real numbers from [month/quarter]. No vanity metrics. Just the truth.",
            "body_structure": [
                "State the headline number (revenue, growth, etc.)",
                "Break down what went well with specific numbers",
                "Break down what went wrong with specific numbers",
                "Share one key learning or decision that resulted",
                "Preview what you're focused on next"
            ],
            "cta_pattern": "Would you share your real numbers publicly? Why or why not? Let me know below.",
            "example_post": (
                "Here are our real numbers from Q4. No vanity metrics. Just the truth.\n\n"
                "Revenue: $127K (up 23% from Q3)\n"
                "Profit margin: 31% (down from 38%)\n"
                "New customers: 47\n"
                "Churned customers: 12\n"
                "Team size: 8 (hired 2 in Q4)\n\n"
                "What went well:\n"
                "- Launched a new pricing tier that drove 60% of new revenue\n"
                "- Reduced support ticket volume by 40% with better documentation\n"
                "- Landed our first enterprise deal ($24K annual)\n\n"
                "What went wrong:\n"
                "- Hiring 2 people compressed margins more than planned\n"
                "- Churn spiked in November (pricing change backlash from legacy users)\n"
                "- Spent $8K on a marketing experiment that generated zero leads\n\n"
                "Key decision: we're pausing hiring in Q1 to let margins recover before growing again.\n\n"
                "Building in public isn't just sharing wins. "
                "It's showing the full picture so others can learn from both.\n\n"
                "Would you share your real numbers publicly? Why or why not? Let me know below."
            ),
            "content_pillars": ["building_in_public", "transparency", "business"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "How We Actually Make Decisions",
            "category": "behind_the_scenes",
            "platform": "instagram",
            "hook_type": "bold_statement",
            "hook_structure": "Everyone sees the launch. Nobody sees the 47 debates that happened before it.",
            "body_structure": [
                "Show a recent decision or launch",
                "Reveal the internal debates and disagreements",
                "Share the criteria you used to decide",
                "Show what you almost did instead",
                "End with the result of the decision"
            ],
            "cta_pattern": "Swipe to see the full behind-the-scenes. Save this for inspiration.",
            "example_post": (
                "Everyone sees the product launch. Nobody sees the 47 debates that happened before it.\n\n"
                "Last month we launched our new dashboard. It looks clean. Users love it. "
                "But getting here was messy.\n\n"
                "The debates:\n"
                "- Should we redesign everything at once or phase it? (2-week argument)\n"
                "- Do we keep the sidebar or switch to top nav? (3 Figma prototypes)\n"
                "- Dark mode now or later? (Our designer threatened to quit over this one)\n\n"
                "How we decided:\n"
                "We put 3 prototypes in front of 20 users. Let them click through. "
                "Measured task completion time. The data killed 2 of our favorite designs.\n\n"
                "What we almost shipped:\n"
                "A beautiful dashboard that tested 40% slower for the most common task. "
                "Pretty but broken.\n\n"
                "The result: 28% faster task completion. NPS went from 32 to 51.\n\n"
                "Lesson: the best product decisions feel boring. "
                "User research > internal opinions, every time.\n\n"
                "Swipe to see the full behind-the-scenes. Save this for inspiration."
            ),
            "content_pillars": ["product_development", "transparency", "team_culture"],
            "format_type": "carousel_caption",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "My Morning Routine (Honest Version)",
            "category": "behind_the_scenes",
            "platform": "instagram",
            "hook_type": "bold_statement",
            "hook_structure": "My morning routine won't go viral because it's boring. But it's the reason I get more done by noon than most people do all day.",
            "body_structure": [
                "Subvert the glamorous morning routine trope",
                "Walk through your actual morning hour by hour",
                "Highlight what you DON'T do (no ice baths, no 4am wake-ups)",
                "Explain the one non-negotiable and why it matters",
                "Close with: routines should serve you, not impress others"
            ],
            "cta_pattern": "What's the most boring part of your routine that actually drives your results? Tell me below.",
            "example_post": (
                "My morning routine won't go viral because it's boring. "
                "But it's the reason I get more done by noon than most people do all day.\n\n"
                "7:00am - Wake up. No alarm. I go to bed early enough that I don't need one.\n\n"
                "7:15am - Coffee + 10 minutes staring at the wall. Not meditating. "
                "Not journaling. Just thinking.\n\n"
                "7:30am - Review my 3 priorities for the day. Written the night before. "
                "If it's not on the list, it doesn't exist until noon.\n\n"
                "8:00am - Deep work on Priority #1. Phone in another room. "
                "No Slack. No email.\n\n"
                "10:00am - Priority #1 is done or significantly advanced. "
                "Only NOW do I check messages.\n\n"
                "What I DON'T do:\n"
                "- No 4am wake-up\n"
                "- No cold plunge\n"
                "- No 90-minute gym session\n"
                "- No gratitude journal\n\n"
                "My one non-negotiable: 2 hours of uninterrupted deep work before the "
                "world gets a piece of me. Everything else is optional.\n\n"
                "Routines should serve your goals, not impress your followers.\n\n"
                "What's the most boring part of your routine that actually drives your results?"
            ),
            "content_pillars": ["productivity", "authenticity", "daily_routine"],
            "format_type": "carousel_caption",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "The Real Cost of Building This Feature",
            "category": "behind_the_scenes",
            "platform": "linkedin",
            "hook_type": "data_point",
            "hook_structure": "That 'simple feature' our users asked for? It took [time], [cost], and [resources]. Here's the breakdown.",
            "body_structure": [
                "Name the feature and show the user request",
                "Break down the actual time investment",
                "Show the hidden complexity users don't see",
                "Share the trade-offs and what you deprioritized",
                "End with what the feature actually cost vs. the value it created"
            ],
            "cta_pattern": "Founders: what 'simple' feature turned into a 3-month saga? I know I'm not the only one.",
            "example_post": (
                "That 'simple feature' our users asked for? It took 6 weeks, $18K, "
                "and one near-burnout. Here's the breakdown.\n\n"
                "The request: 'Can we export reports to PDF?'\n"
                "Sounds like a weekend project, right?\n\n"
                "Reality:\n"
                "- Week 1-2: Research PDF libraries. Three options. "
                "All break on tables with 100+ rows.\n"
                "- Week 3: Build custom rendering engine. "
                "Turns out CSS-to-PDF is a dark art.\n"
                "- Week 4: Handle 47 edge cases. Charts, images, dynamic content, "
                "multi-page layouts.\n"
                "- Week 5: QA across browsers and locales. "
                "Japanese characters broke everything.\n"
                "- Week 6: Performance optimization. First version took 45 seconds "
                "per export. Got it to 3 seconds.\n\n"
                "What we deprioritized:\n"
                "- Mobile responsive redesign (pushed 2 months)\n"
                "- Two integration partnerships (deferred)\n\n"
                "Cost: $18K in developer time\n"
                "Value: Reduced churn by 8% (our #1 cancellation reason was 'can't export data')\n\n"
                "ROI: paid for itself in 3 weeks.\n\n"
                "Founders: what 'simple' feature turned into a 3-month saga? "
                "I know I'm not the only one."
            ),
            "content_pillars": ["product_development", "building_in_public", "engineering"],
            "format_type": "list_post",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },

        # ========================================================
        # SOCIAL PROOF (3) - All platforms
        # ========================================================
        {
            "template_id": str(uuid.uuid4()),
            "title": "Client Success Story Spotlight",
            "category": "social_proof",
            "platform": "linkedin",
            "hook_type": "data_point",
            "hook_structure": "[Client/User] went from [before state] to [after state] in [timeframe]. Here's how.",
            "body_structure": [
                "Introduce the client and their starting point",
                "Describe the challenge they were facing",
                "Walk through the approach or solution (without overselling)",
                "Show the measurable results",
                "Extract a lesson that anyone can apply"
            ],
            "cta_pattern": "If you're facing a similar challenge, drop a comment or DM me. Happy to share what worked.",
            "example_post": (
                "One of our clients went from 2% reply rate on outreach to 34% in 90 days. "
                "Here's how.\n\n"
                "Starting point: Sarah runs a B2B SaaS company. 10-person team. "
                "Outbound was their biggest growth channel but it was dying. "
                "2% reply rate. Team was demoralized.\n\n"
                "The challenge: They were sending beautifully designed HTML emails "
                "with company logos and formatted CTAs. It looked professional.\n\n"
                "The problem? It also looked like marketing. And marketing emails get deleted.\n\n"
                "The approach:\n"
                "1. Switched from HTML to plain text emails\n"
                "2. Cut email length from 200 words to 50 words\n"
                "3. Personalized the first line using LinkedIn activity (not company info)\n"
                "4. Changed CTA from 'Book a demo' to 'Would this be useful for you?'\n\n"
                "Results after 90 days:\n"
                "- Reply rate: 2% to 34%\n"
                "- Booked meetings: 3/month to 22/month\n"
                "- Pipeline value: 4x increase\n"
                "- Team morale: through the roof\n\n"
                "The lesson anyone can apply: make your outreach feel like a human "
                "reaching out, not a company marketing.\n\n"
                "If you're facing a similar challenge, drop a comment or DM me. "
                "Happy to share what worked."
            ),
            "content_pillars": ["case_study", "sales", "social_proof"],
            "format_type": "story",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "Milestone Celebration With Lessons",
            "category": "social_proof",
            "platform": "x",
            "hook_type": "data_point",
            "hook_structure": "We just hit [milestone]. [N] things I'd do differently if I started over today:",
            "body_structure": [
                "Announce the milestone (keep it humble)",
                "List 4-5 things you'd do differently",
                "For each, share the lesson behind it",
                "Thank specific people or groups (not generic gratitude)",
                "Share what's next"
            ],
            "cta_pattern": "Thanks for being part of this journey. What's a milestone you're working toward right now?",
            "example_post": (
                "We just hit 10,000 users. 5 things I'd do differently if I started over today:\n\n"
                "1. I'd charge from day one.\n"
                "We gave away the product free for 6 months to 'build traction.' "
                "All we built was a list of users who didn't value paying.\n\n"
                "2. I'd hire a customer success person before a second engineer.\n"
                "We built features nobody asked for while ignoring the users we had.\n\n"
                "3. I'd write content from week one.\n"
                "Our best growth channel (organic content) took 8 months to start "
                "because we started 8 months late.\n\n"
                "4. I'd talk to 5 users every single week.\n"
                "Not surveys. Real conversations. The insights are 10x richer.\n\n"
                "5. I'd take care of my health from the start.\n"
                "Burned out at month 14. Recovery took 3 months. "
                "Consistent exercise would have prevented it.\n\n"
                "Thanks to everyone who believed in this when we were at user #7.\n\n"
                "What's a milestone you're working toward right now?"
            ),
            "content_pillars": ["milestones", "building_in_public", "lessons_learned"],
            "format_type": "thread",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "template_id": str(uuid.uuid4()),
            "title": "User Feedback Turned Into Action",
            "category": "social_proof",
            "platform": "instagram",
            "hook_type": "bold_statement",
            "hook_structure": "A user sent us this DM. It changed our entire product roadmap.",
            "body_structure": [
                "Show the user message or feedback (with permission/anonymized)",
                "Explain what it revealed about your blind spot",
                "Describe the change you made in response",
                "Share the impact of that change",
                "Tie it to a broader principle about listening to users"
            ],
            "cta_pattern": "We build for you. What's one thing you wish we'd change? Tell us in the comments.",
            "example_post": (
                "A user sent us this DM last month. It changed our entire product roadmap.\n\n"
                "The message:\n"
                "'I love your tool but I stopped using it because I can't find anything "
                "I created last week. The search is broken and there's no way to organize my content.'\n\n"
                "Our first reaction: 'Search works fine, what are they talking about?'\n\n"
                "Then we tested it ourselves with 50+ content pieces. They were right. "
                "Finding anything older than 3 days was painful.\n\n"
                "We had been so focused on creation features that we completely neglected "
                "the content library experience.\n\n"
                "What we changed:\n"
                "- Added full-text search across all content\n"
                "- Built folders and tagging system\n"
                "- Added 'recently edited' and 'favorites' sections\n"
                "- Shipped it in 2 weeks (moved everything else)\n\n"
                "Impact: daily active usage went up 40% in the first week. "
                "Users weren't creating less - they were losing what they created.\n\n"
                "The principle: your loudest feature requests might not be your most "
                "important ones. Sometimes the quiet frustrations cause the most churn.\n\n"
                "We build for you. What's one thing you wish we'd change? "
                "Tell us in the comments."
            ),
            "content_pillars": ["customer_feedback", "product_development", "social_proof"],
            "format_type": "carousel_caption",
            "author_id": "system",
            "is_official": True,
            "is_active": True,
            "upvotes": 0,
            "uses_count": 0,
            "views_count": 0,
            "created_at": now,
            "updated_at": now,
        },
    ]

    return templates


async def seed():
    """Insert seed templates into the database (idempotent)."""
    count = await db.templates.count_documents({})
    if count > 10:
        print(f"Templates collection already has {count} documents. Skipping seed.")
        return

    templates = get_seed_templates()
    result = await db.templates.insert_many(templates)
    print(f"Successfully seeded {len(result.inserted_ids)} templates into the marketplace.")


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(seed())
