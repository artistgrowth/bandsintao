## Contributing

All changes are submitted as pull requests from personal forks. Before you do anything else,
[go fork yourself][fork-yourself]. Any changes will need to be pushed to one's fork first and
then a pull request will be issued to the [canonical repo][canonical].

## Commits

* Commits should always represent a unit-of-work and stand on their own.
* Please don't commit broken code and never, ever mix changes for different purposes in a single commit.
* Run unit tests before submitting code for review.
* Avoid merging pull requests of one's own code.
* You break the build... you fix it.
* Notify team members if merged changes will cause disruption in their normal workflow.

### Commit Messages
Commit messages should include a grammatically-correct message adhering to the following guidelines:

* Separate subject from body with a blank line
* Limit the subject line to 50 characters
* Capitalize the subject line
* Do not end the subject line with a period
* Use the imperative mood in the subject line
* Wrap the body at 72 characters
* Use the body to explain what and why vs. how

        Derezz the master control program

        More detailed explanatory text, if necessary. Wrap it to about 72
        characters or so. In some contexts, the first line is treated as the
        subject of the commit and the rest of the text as the body. The
        blank line separating the summary from the body is critical (unless
        you omit the body entirely); various tools like `log`, `shortlog`
        and `rebase` can get confused if you run the two together.

        Explain the problem that this commit is solving. Focus on why you
        are making this change as opposed to how (the code explains that).
        Are there side effects or other unintuitive consequences of this
        change? Here's the place to explain them.

        Further paragraphs come after blank lines.

        * Bullet points are okay, too
        * Typically a hyphen or asterisk is used for the bullet, preceded
          by a single space, with blank lines in between, but conventions
          vary here

        If you use an issue tracker, put references to them at the bottom,
        like this:

        [Delivers: #123]
        See also: [#456, #789]

* Commits can and should reference stories in our ticketing system by including `[(Finishes|Fixes|Delivers) #<TRACKER_STORY_ID>]` anywhere in the message. See the [Pivotal Tracker API Reference](https://www.pivotaltracker.com/help/api?version=v3#scm_post_commit_message_syntax) for more details.
    * Use `Delivers` when the ticket should be auto-delivered in the ticketing system, _i.e. ready for external testing_.
    * Use `Finished` when the ticket should be auto-finished in the ticketing system.

> One can also reference other people or organization groups (and send them a notification) in commit messages using `@<someone's GitHub username>`. For example:

    Remove dependency on flux capacitor.

    @fredpalmer would probably want to see this.  Also @davidsidlinger is a cotton-headed ninny muggins.

_Pretty much anything in [GitHub Markdown][github-markdown] works in a commit message._

## Branching Model

The branching model we use is called [Git-Flow][git-flow]. In summary:

  * `master`
    * **Contains:** The current production codebase.
    * **Exists in:** The [canonical repo][canonical] and, optionally, a personal fork.
    * **Merged to:** Nothing. However, the `develop` branch is initially created from this branch.
  * `develop`
    * **Contains:** Feature-complete work that is staged for the next release.
    * **Exists in:** The [canonical repo][canonical] and, optionally, a personal fork.
    * **Merged to:** `feature/<name>` branches currently being developed
  * `feature/<name>` (e.g. `feature/user-profiles`, `feature/share-buttons`)
    * **Contains:** Work in progress related to a _single_ feature.
    * **Exists in:** A personal fork.
    * **Created from:** The `develop` branch.
    * **Merged to:** The `develop` branch, when work is complete, tested, and approved.
  * `bug/<name>` (e.g. `bug/ie-margins-busted`, `bug/rework-model-hierarchy`)
    * **Contains:** Work in progress related to a _single_ fix, which is _not_ important enough to require an independent update to production.
    * **Exists in:** A personal fork.
    * **Created from:** The `develop` branch.
    * **Merged to:** The `develop` branch, when work is complete, tested, and approved.
  * `release/<year-month-day>`
    * **Contains:** A release candidate intended for an impending release.
    * **Exists in:** The [canonical repo][canonical]
    * **Merged to:** The `master` branch immediately after a release.
  * `hotfix/<name>` (e.g. `hotfix/profile-javascript-error`, `hotfix/database-deadlocks`)
    * **Contains:** Work in progress related to a _single_ fix, which is important enough to require an independent update to production or a release branch.
    * **Exists in:** A personal fork.
    * **Created from:** The `master` branch or a `release/<year-month-day>` branch if there is a release candidate in progress.
    * **Merged to:** A `release/<year-month-day>` branch, when work is complete, tested, and approved.

If your branches aren't named appropriately they will be rejected in pull requests.

### Other Rules
  * There should never be an update to the [canonical repo][canonical] outside of the confines of a pull request during the course of normal development.

[fork-yourself]: ../fork "Fork this repo"
[canonical]: ../ "Canonical repo"
[git-flow]: http://nvie.com/posts/a-successful-git-branching-model/ "Git-Flow branching model"
[github-markdown]: https://help.github.com/articles/github-flavored-markdown "Github-flavored Markdown"
