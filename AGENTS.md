Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

1. Think Before Coding
   Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask. 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes
   Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution
   Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
   Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**CRITICAL RULES**

Please always explain the user in simpler terms. The coding must be simple, precise and upto the point, nothing fancy until mentioned. Always keep the human in the loop for any critical decision. for any module you make, make sure the user learns along with you, everything from the tech stack you are using to the coding part always walk the user through it. Explain it in the simplest way possible because the tech stack is new to the user. First provide a summary of what we are trying to do i.e.- WHAT, WHY AND HOW and then we will proceed further.Use plan mode to develop any feature.

Also make sure to break up everything in modules and then implement each module, doing that help us to test a particular module. for ex- You developed a retiever then you need to test is properly using seperate tesing module(use libraries like deepeval for that and use metrics-i.e. here recall@k and precision@k ) and properly evaluate the module and tell me the results at the end and then only proceed to next module

and also keep names for each module, for ex- retriever.py, I want you to develop each module independently and then wire them up by using an orchestrator. follow proper system design principle.

Use skills and plugins wherever possible.
