# TODO

## Backlog

### Phase 1: CLI Infrastructure

- [x] **1.1: Add Rich and prompt_toolkit dependencies**
  - Location: `pyproject.toml`
  - Add `rich>=13.0.0` to dependencies
  - Add `prompt_toolkit>=3.0.0` to dependencies
  - Add `python-dotenv` to dependencies
  - Run `pip install -e .` or `uv sync` to install dependencies

- [x] **1.2: Create CLI package structure**
  - Location: `src/simple_email_gw/cli/`
  - Create `__init__.py` with package exports
  - Create empty module files: `app.py`, `session.py`, `commands.py`, `display.py`, `theme.py`
  - Add CLI entry point to `pyproject.toml` scripts section: `email-gw-cli = "simple_email_gw.cli.app:main"`

- [x] **1.3: Implement Session Manager**
  - Location: `src/simple_email_gw/cli/session.py`
  - Create `Session` class with attributes:
    - `current_account: EmailAccount | None`
    - `current_folder: str` (default: "INBOX")
    - `_imap_client: IMAPClient | None`
    - `_smtp_client: SMTPClient | None`
  - Methods:
    - `set_account(account: EmailAccount)` - Set active account
    - `set_folder(folder: str)` - Set current folder
    - `async get_imap_client()` - Get or create IMAP client
    - `async get_smtp_client()` - Get or create SMTP client
    - `async disconnect()` - Cleanup all connections
  - Integration: Use existing `ConnectionPool` from `simple_email_gw.connections.pool`

- [x] **1.4: Implement Display Utilities**
  - Location: `src/simple_email_gw/cli/display.py`
  - Import Rich: `from rich.console import Console`, `from rich.table import Table`, `from rich.panel import Panel`, `from rich.syntax import Syntax`
  - Functions:
    - `display_accounts(console: Console, accounts: list[dict])` - Format accounts table
    - `display_folders(console: Console, folders: list[dict])` - Format folders table
    - `display_emails(console: Console, messages: list[dict])` - Format emails table with columns: ID, From, Subject, Date, Status
    - `display_email(console: Console, email: dict)` - Format single email panel with syntax-highlighted headers
    - `display_error(console: Console, error: str, suggestion: str | None = None)` - Format error panel
    - `display_success(console: Console, message: str)` - Format success panel
    - `display_warning(console: Console, message: str)` - Format warning panel
  - Theme-aware colors using theme.py

- [x] **1.5: Implement CLI Application Core**
  - Location: `src/simple_email_gw/cli/app.py`
  - Create `EmailCLI` class with:
    - Attributes:
      - `console: Console` - Rich console instance
      - `session: Session` - Session state manager
      - `config: ServerConfig` - Server configuration
      - `prompt_session: PromptSession` - prompt_toolkit session for async input
    - Methods:
      - `__init__()` - Initialize console, session, load config
      - `async run()` - Main REPL loop with proper async handling
      - `async handle_command(input: str)` - Parse and execute commands
      - `get_prompt()` - Build prompt string (account:folder>)
      - `async connect_account(name: str)` - Connect to specified account
      - `display_help()` - Show available commands
      - `display_status()` - Show current session state
      - `toggle_theme()` - Toggle between light/dark color themes
  - Implement command parser:
    - Split input by whitespace
    - Command is first word
    - Arguments are remaining words
    - Handle quoted strings for subjects/folders with spaces
  - Error handling:
    - Catch `KeyboardInterrupt` - continue REPL
    - Catch `EOFError` - exit gracefully
    - Catch all exceptions - display error panel, continue REPL
  - Async pattern:
    - Use `asyncio.run()` in `main()` entry point
    - Use `prompt_toolkit.patch_stdout` for proper output handling
    - Use `PromptSession.prompt_async()` for async input
  - Load environment variables from .env file on startup

- [x] **1.6: Implement Theme System**
  - Location: `src/simple_email_gw/cli/theme.py`
  - Create `ThemeType` enum (LIGHT, DARK)
  - Create `ColorTheme` class with theme-aware colors:
    - Light theme: darker colors for contrast on white backgrounds
    - Dark theme: bright colors for contrast on dark backgrounds
  - Create `ThemeManager` singleton for managing theme state
  - Add `theme` command to toggle between light and dark themes
  - Update all display functions to use theme colors

- [x] **1.5: Implement CLI Application Core**
  - Location: `src/simple_email_gw/cli/app.py`
  - Create `EmailCLI` class with:
    - Attributes:
      - `console: Console` - Rich console instance
      - `session: Session` - Session state manager
      - `config: ServerConfig` - Server configuration
      - `prompt_session: PromptSession` - prompt_toolkit session for async input
    - Methods:
      - `__init__()` - Initialize console, session, load config
      - `async run()` - Main REPL loop with proper async handling
      - `async handle_command(input: str)` - Parse and execute commands
      - `get_prompt()` - Build prompt string (account:folder>)
      - `async connect_account(name: str)` - Connect to specified account
      - `display_help()` - Show available commands
      - `display_status()` - Show current session state
  - Implement command parser:
    - Split input by whitespace
    - Command is first word
    - Arguments are remaining words
    - Handle quoted strings for subjects/folders with spaces
  - Error handling:
    - Catch `KeyboardInterrupt` - continue REPL
    - Catch `EOFError` - exit gracefully
    - Catch all exceptions - display error panel, continue REPL
  - Async pattern:
    - Use `asyncio.run()` in `main()` entry point
    - Use `prompt_toolkit.patch_stdout` for proper output handling
    - Use `PromptSession.prompt_async()` for async input

### Phase 2: Account & Folder Commands

- [x] **2.1: Implement accounts command**
  - Location: `src/simple_email_gw/cli/app.py`
  - Function: `async _cmd_accounts(cli: EmailCLI)`
  - Behavior:
    - Load accounts from config using `get_accounts()`
    - Display table with columns: Name, Username, Status
    - Status shows "connected" for current account, "available" for others
    - Handle no accounts case: display error with configuration instructions
  - Error handling:
    - Catch `ValueError` - display configuration error
    - Catch general exceptions - display generic error

- [x] **2.2: Implement use command**
  - Location: `src/simple_email_gw/cli/app.py`
  - Function: `async _cmd_use(cli: EmailCLI, name: str)`
  - Behavior:
    - Validate account name exists in config
    - Set session's current account
    - Connect IMAP client using `session.get_imap_client()`
    - Display success message with account name
    - Set current folder to "INBOX"
  - Error handling:
    - Account not found: display error with available accounts
    - Authentication failure: display error, suggest checking credentials
    - Network failure: display error, suggest checking network
  - Default behavior:
    - If no accounts configured, display error
    - If only one account, auto-select it on startup

- [x] **2.3: Implement folders command**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Function: `async cmd_folders(cli: EmailCLI)`
  - Behavior:
    - Check session has active account
    - Use `session.get_imap_client()` to get client
    - Call `client.list_folders()`
    - Display table with columns: Name, Flags, Delimiter
    - Use Rich spinner during operation: `console.status("Fetching folders...")`
  - Error handling:
    - No account selected: display error, suggest using `use` command
    - IMAP error: display error, suggest checking connection
  - TDD: Create test stubs in `tests/cli/test_commands.py` first

- [x] **2.4: Implement cd command**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Function: `async cmd_cd(cli: EmailCLI, folder: str | None)`
  - Behavior:
    - Check session has active account
    - Use `session.get_imap_client()` to get client
    - Call `client.select_folder(folder or "INBOX")`
    - Update `session.current_folder`
    - Display success message with message count
  - Error handling:
    - Folder not found: display error with available folders
    - No account selected: display error, suggest using `use` command
  - TDD: Create test stubs in `tests/cli/test_commands.py` first

### Phase 3: Email Listing & Viewing Commands

- [x] **3.1: Implement ls command**
  - Location: `src/simple_email_gw/cli/commands.py` and `src/simple_email_gw/cli/display.py`
  - UX Design: See `analysis/ux-ls-command.md`
  - Function: `async cmd_ls(cli: EmailCLI, limit: int = 50)`
  - Behavior:
    - Check session has active account
    - Parse and validate `limit` argument; clamp to 1-500 with warning if exceeded
    - Use `session.get_imap_client()` to get client
    - Call `client.search(folder=session.current_folder, criteria="ALL", limit=limit)`
    - Fetch messages sequentially in a loop (single IMAP client; parallelism is limited by internal lock)
    - Display table with columns: ID, From, Subject, Date, Status (read/unread)
    - Use Rich two-phase spinner: "Searching folder..." then "Fetching N messages..."
    - Cache fetched emails in session for faster `show` command
  - UX requirements (display.py):
    - Table uses fixed/max column widths with `overflow="ellipsis"` for From and Subject
    - Unread emails use bold + color accent (`ansiblue`/`ansicyan`) plus a `●` indicator
    - Table caption shows folder name and message count
    - Empty folder shows contextual warning with folder name and tip to use `folders`/`cd`
    - If folder has more messages than `limit`, show hint to load more
  - Error handling:
    - No account selected: display error, preserve REPL flow
    - No messages: display contextual warning (folder name + tip)
    - IMAP search/fetch error: display error panel with actionable suggestion
    - Per-message fetch failure: render placeholder row, continue listing remainder
    - Ctrl+C during fetch: cancel gracefully, stop spinner, return to prompt
  - Requires: Theme update for `unread_indicator` color

- [x] **3.2: Implement show command**
  - Location: `src/simple_email_gw/cli/app.py`
  - Function: `async cmd_show(cli: EmailCLI, message_id: str)`
  - Behavior:
    - Check session has active account
    - Check if message is cached from previous `ls`
    - If not cached, fetch using `client.fetch_message(message_id, folder=session.current_folder)`
    - Display email in Rich Panel with:
      - Syntax-highlighted headers (From, To, Subject, Date)
      - Plain text body
      - Attachments list if present
    - Use Rich spinner during fetch
  - Display:
    - Use `Panel` for overall container
    - Use `Syntax` for header display
    - For long bodies, use `console.pager()` or paginate
  - Error handling:
    - Invalid message ID: display error with suggestion to use `ls`
    - No account selected: display error
    - Fetch error: display error
  - **Note**: `display_email()` already implemented in `display.py` with tests. Need to wire up `_cmd_show()` in `app.py`.

- [x] **3.3: Implement email caching**
  - Location: `src/simple_email_gw/cli/session.py`
  - Add to `Session` class:
    - `_email_cache: dict[str, dict]` - Cache of fetched emails by ID
    - `_cache_folder: str` - Folder the cache is for
    - `cache_email(message_id: str, email: dict)` - Add to cache
    - `get_cached_email(message_id: str) -> dict | None` - Get from cache
    - `clear_cache()` - Clear cache when changing folders
  - Integration:
    - `cmd_ls` populates cache
    - `cmd_show` uses cache if available

### Phase 4: Email Composition Commands

- [x] **4.1: Implement write command - core flow**
  - Location: `src/simple_email_gw/cli/app.py`
  - UX Design: See `analysis/ux-email-composition.md` Section 1
  - Function: `async _cmd_write(self, args: list[str])`
  - Behavior:
    - Check session has active account; if not, `display_error()` with suggestion
    - Parse primary recipients from args (comma-separated via shlex)
    - Validate each recipient using `validate_email()`; check whitelist
    - Prompt for subject; allow empty but show `display_warning()`
    - Prompt for CC recipients (optional, Enter to skip); validate and whitelist-check; re-prompt on invalid input
    - Prompt for BCC recipients (optional, Enter to skip); same validation behavior
    - Collect multi-line body via `get_body_input()`; Ctrl+D to finish
    - Handle empty body: warn and ask "Send anyway? (y/n)"
    - Handle Ctrl+C at any step: cancel compose, print "[dim]Compose cancelled.[/dim]", return to REPL
  - Integration:
    - Use `session.get_smtp_client()` to get SMTP client
    - Call `client.send_email(to, subject, body, cc, bcc)`
  - Acceptance Criteria:
    - `write alice@example.com,bob@example.com` starts the wizard
    - Invalid primary recipient aborts to REPL with error panel
    - Invalid CC/BCC re-prompts that field only, does not abort entire flow
    - Empty subject proceeds with warning panel
    - Empty body shows warning + confirmation before preview
    - Ctrl+C at any prompt cancels compose and returns to REPL
    - Body input supports multi-line text terminated by Ctrl+D

- [x] **4.2: Implement write command - preview and confirmation**
  - Location: `src/simple_email_gw/cli/app.py`
  - UX Design: See `analysis/ux-email-composition.md` Section 2
  - Add to `_cmd_write` after body collection:
    - Display preview using `confirm_send()` utility:
      - Metadata table (From, To, CC, BCC, Subject) with field labels in `theme.secondary`
      - Body preview Panel with first 500 chars; append `... (N more characters)` if truncated
    - Prompt: "Send email? (y/n/e): "
      - `y`/`yes`: send with Rich spinner "Sending email..."
      - `n`/`no`: discard; print "[dim]Email discarded.[/dim]"
      - `e`/`edit`: return to body input with existing text preserved
      - Invalid input: re-prompt
    - On send success: `display_success()` with recipient list
    - On send failure: `display_error()` with actionable suggestion
  - Acceptance Criteria:
    - Preview screen is scannable and fits terminals down to 40 columns
    - Body preview truncates at 500 chars with a dim continuation note
    - Confirmation accepts y/n/e and handles case-insensitive input
    - Edit option returns user to body input without losing prior text
    - Spinner appears during SMTP operation
    - Success/error panels use existing theme colors consistently

- [x] **4.3: Implement reply command**
  - Location: `src/simple_email_gw/cli/app.py`
  - UX Design: See `analysis/ux-email-composition.md` Section 3
  - Function: `async _cmd_reply(self, args: list[str])`
  - Behavior:
    - Check session has active account
    - Validate message_id is numeric; if not, `display_error()`
    - Fetch original email (use session cache first; else IMAP fetch with spinner)
    - If not found: `display_error()` suggesting `ls`
    - Display "Replying to" context panel with From, Subject, Date
    - Pre-populate To from original From
    - Pre-populate Subject with "Re: {original_subject}"; avoid double "Re:" prefix
    - Display quoted original body above input area using `theme.secondary` for quote lines
    - Collect reply body via `get_body_input()`
    - Preview and confirmation identical to write command (`confirm_send()`)
  - Integration:
    - Use `session.get_smtp_client()` and `client.reply_email()`
    - Pass `in_reply_to` and `references` from original message headers
  - Acceptance Criteria:
    - Context panel appears before body input so user remembers the original email
    - Quoted original body is displayed as read-only context, not sent verbatim (send only user-typed text)
    - Subject deduplication prevents "Re: Re:" prefixes
    - Preview/confirmation behavior matches write command exactly
    - Ctrl+C cancels compose; invalid message ID returns to REPL with error

- [x] **4.4: Implement reusable input utilities for composition**
  - Location: `src/simple_email_gw/cli/display.py`
  - UX Design: See `analysis/ux-email-composition.md` Sections 1, 4, 5
  - Function: `get_recipients_input(console: Console, prompt: str) -> list[str]`
    - Display prompt and dim hint "Enter comma-separated email addresses:"
    - Read one line via `input()`
    - Parse comma-separated values, strip whitespace
    - Validate each with `validate_email()`
    - Check whitelist; if any blocked, show error and return empty list so caller can re-prompt
    - Return list of valid addresses
    - Handle EOFError (Ctrl+D) -> return empty list
  - Function: `get_body_input(console: Console, prompt: str = "Enter email body. Press Ctrl+D when done.") -> str`
    - Display prompt and dim hint
    - Read lines via `input()` until EOFError (Ctrl+D)
    - Handle KeyboardInterrupt -> re-raise so caller can cancel compose
    - Return joined lines
  - Function: `confirm_send(console: Console, preview: dict[str, Any]) -> str`
    - Display metadata table and body preview panel per UX spec
    - Prompt "Send email? (y/n/e): " via `input()`
    - Return normalized response: "y", "n", or "e"
    - Handle EOFError -> return "n"
    - Handle KeyboardInterrupt -> re-raise
  - Acceptance Criteria:
    - Utilities are theme-aware where applicable (preview uses `theme.secondary` for labels)
    - `get_recipients_input` returns only fully validated and whitelisted addresses
    - `get_body_input` supports Ctrl+D termination and propagates Ctrl+C
    - `confirm_send` returns a three-state response (y/n/e) and renders preview consistently
    - All utilities use plain `input()` to avoid `prompt_toolkit` nesting issues

### Phase 5: Additional Email Commands

- [ ] **5.1: Implement delete command**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Function: `async cmd_delete(cli: EmailCLI, message_id: str)`
  - Behavior:
    - Check session has active account
    - Confirm: "Delete message {message_id}? (y/n): "
    - Use `session.get_imap_client()` to get client
    - Call `client.delete_message(message_id, folder=session.current_folder)`
    - Clear message from cache
    - Display success message
  - Error handling:
    - Invalid message ID: display error
    - No account selected: display error

- [ ] **5.2: Implement move command**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Function: `async cmd_move(cli: EmailCLI, message_id: str, dest_folder: str)`
  - Behavior:
    - Check session has active account
    - Validate destination folder exists
    - Confirm: "Move message {message_id} to {dest_folder}? (y/n): "
    - Use `session.get_imap_client()` to get client
    - Call `client.move_message(message_id, session.current_folder, dest_folder)`
    - Clear message from cache
    - Display success message
  - Error handling:
    - Invalid message ID: display error
    - Invalid folder: display error with folder list
    - No account selected: display error

### Phase 6: Session & Utility Commands

- [ ] **6.1: Implement help command**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Function: `cmd_help(cli: EmailCLI)`
  - Behavior:
    - Display table with columns: Command, Description
    - Commands:
      - `accounts` - List configured email accounts
      - `use <account>` - Select account for operations
      - `folders` - List folders in current account
      - `cd [folder]` - Change to folder (default: INBOX)
      - `ls [limit]` - List emails in current folder
      - `show <id>` - Display email by ID
      - `write <to>` - Compose new email
      - `reply <id>` - Reply to email
      - `delete <id>` - Delete email
      - `move <id> <folder>` - Move email to folder
      - `status` - Show current session state
      - `help` - Show this help
      - `quit` - Exit the CLI
    - Use Rich table for formatting

- [ ] **6.2: Implement status command**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Function: `cmd_status(cli: EmailCLI)`
  - Behavior:
    - Display panel with current session state:
      - Account: {name} ({username}) or "None"
      - Folder: {folder} or "None"
      - Connection status: "Connected" or "Disconnected"
    - If account selected, show additional info:
      - IMAP server: {imap_host}:{imap_port}
      - SMTP server: {smtp_host}:{smtp_port}

- [ ] **6.3: Implement quit command**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Function: `async cmd_quit(cli: EmailCLI)`
  - Behavior:
    - Call `session.disconnect()` to cleanup connections
    - Display "Goodbye!" message
    - Exit REPL loop

- [ ] **6.4: Implement keyboard interrupt handling**
  - Location: `src/simple_email_gw/cli/app.py`
  - Add to `run()` method:
    - Catch `KeyboardInterrupt` during command input
    - Display: "Press Ctrl+D to exit or type 'quit'"
    - Continue REPL loop
    - During async operations, catch `KeyboardInterrupt`
    - Cancel operation and return to prompt

### Phase 7: Error Handling & Edge Cases

- [ ] **7.1: Implement comprehensive error handling**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Create error handling wrapper:
    - Function: `async handle_errors(coro)` - decorator for commands
    - Catch specific exceptions:
      - `ValueError` - validation errors
      - `RuntimeError` - connection/operation errors
      - `WhitelistError` - recipient whitelist violations
      - `SecurityError` - security violations
      - `RateLimitError` - rate limit exceeded
      - `ConnectionError` - network issues
      - `TimeoutError` - operation timeouts
    - Map errors to user-friendly messages:
      - Auth failure -> "Authentication failed. Check credentials."
      - Network error -> "Connection failed. Check network."
      - Rate limit -> "Rate limit exceeded. Please wait."
      - Whitelist -> "Recipient not in whitelist."
    - Use `display_error()` with suggestion parameter

- [ ] **7.2: Implement rate limit handling**
  - Location: `src/simple_email_gw/cli/app.py`
  - Add rate limit awareness:
    - Catch `RateLimitError` from connection pool
    - Display warning with wait suggestion
    - Queue operations if possible (future enhancement)
    - Currently: just display error and allow retry

- [ ] **7.3: Implement graceful degradation**
  - Location: `src/simple_email_gw/cli/app.py`
  - Handle missing configuration:
    - No accounts configured: display error with setup instructions
    - Invalid configuration: display specific error
  - Handle missing dependencies:
    - Rich not installed: display error with install instructions
    - prompt_toolkit not installed: display error with install instructions

- [ ] **7.4: Implement input validation**
  - Location: `src/simple_email_gw/cli/commands.py`
  - Validate all user inputs:
    - Account names: check against config
    - Folder names: escape special characters
    - Message IDs: validate numeric format
    - Email addresses: validate format and whitelist
    - Subjects: sanitize for CRLF injection
    - Bodies: limit size, warn on very large bodies

### Phase 8: Testing

- [ ] **8.1: Create unit tests for session manager**
  - Location: `tests/cli/test_session.py`
  - Test account selection
  - Test folder management
  - Test client caching
  - Test connection cleanup
  - Test email caching

- [ ] **8.2: Create unit tests for display utilities**
  - Location: `tests/cli/test_display.py`
  - Test table formatting
  - Test panel formatting
  - Test error panel formatting
  - Test body input handling

- [ ] **8.3: Create unit tests for command handlers**
  - Location: `tests/cli/test_commands.py`
  - Test each command with mocked clients
  - Test error handling for each command
  - Test input validation
  - Test async operation flow

- [ ] **8.4: Create integration tests for CLI workflow**
  - Location: `tests/cli/test_integration.py`
  - Test complete workflows:
    - Account selection -> folder navigation -> email viewing
    - Email composition -> preview -> send
    - Reply workflow
    - Error recovery workflows
  - Use mock IMAP/SMTP clients
  - Test with simulated network errors
  - Test with simulated auth errors

- [ ] **8.5: Manual testing checklist**
  - Create testing script for manual testing
  - Test with Gmail account (requires app password)
  - Test with iCloud account (requires app password)
  - Test network disconnection scenarios
  - Test rate limiting scenarios
  - Test whitelist enforcement
  - Test keyboard interrupt handling
  - Test all commands with various inputs

### Phase 9: Documentation

- [ ] **9.1: Update README.md**
  - Add section: "## Interactive CLI"
  - Add installation instructions for CLI dependencies
  - Add usage example:
    ```bash
    # Start interactive CLI
    email-gw-cli

    # CLI session example
    Email Gateway CLI
    Type 'help' for available commands.

    > accounts
    Name      Username           Status
    work      work@example.com    available
    personal  me@icloud.com       available

    > use work
    Connected to work (work@example.com)

    work:INBOX> folders
    Name              Flags
    INBOX             \HasNoChildren
    Sent              \HasNoChildren
    Drafts            \HasNoChildren
    Trash             \HasNoChildren

    work:INBOX> ls 10
    ID  From                 Subject                    Date
    1    sender@example.com   Test Email                 2026-05-08
    2    boss@company.com     Project Update             2026-05-07

    work:INBOX> show 1
    From: sender@example.com
    To: work@example.com
    Subject: Test Email
    Date: 2026-05-08 10:30:00

    This is the email body.

    work:INBOX> write recipient@example.com
    Subject: Reply
    CC (press Enter to skip):
    BCC (press Enter to skip):
    Enter email body. Press Ctrl+D when done:
    This is my reply.
    <Ctrl+D>

    Preview:
    To: recipient@example.com
    Subject: Reply
    Body: This is my reply.

    Send email? (y/n/e): y
    Email sent successfully to recipient@example.com

    work:INBOX> quit
    Goodbye!
    ```
  - Document all commands with examples
  - Document Ctrl+D for finishing body input

- [ ] **9.2: Create CLI reference documentation**
  - Location: `docs/cli.rst`
  - Document installation
  - Document all commands:
    - Syntax
    - Arguments
    - Examples
    - Error handling
  - Document keyboard shortcuts:
    - Ctrl+D - finish body input
    - Ctrl+C - cancel operation
    - Ctrl+D on empty prompt - exit CLI
  - Add to docs index

- [ ] **9.3: Update pyproject.toml entry points**
  - Add console script: `email-gw-cli = "simple_email_gw.cli.app:main"`
  - Document in README.md

### Phase 10: Future Enhancements (Optional)

- [ ] **10.1: Add attachment support**
  - Commands: `download <message_id> <filename>`, `attach <filename>`
  - Workspace confinement for downloads
  - Progress indicators for large attachments

- [ ] **10.2: Add HTML email viewing**
  - Detect HTML emails
  - Render HTML in terminal using `rich.markdown` or browser launch
  - Option to view raw HTML

- [ ] **10.3: Add email search**
  - Command: `search <criteria>`
  - Support IMAP search criteria
  - Examples: `search FROM sender@example.com`, `search SUBJECT project`

- [ ] **10.4: Add configuration management**
  - Command: `config` to view current configuration
  - Command: `set <key> <value>` for runtime config changes
  - Persistent configuration file

- [ ] **10.5: Add account management**
  - Command: `add-account` to add new account
  - Command: `remove-account` to remove account
  - Secure password storage

## Done

None yet.
