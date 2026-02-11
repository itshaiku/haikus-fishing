# Contributing to Haiku Fishing

Thank you for considering contributing to this project!

## How to Contribute

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** - Keep commits focused and test thoroughly
4. **Commit with clear messages**
   ```bash
   git commit -m "Add: feature description"
   git commit -m "Fix: bug description"
   git commit -m "Update: improvement description"
   ```
5. **Push to your branch**
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** with a detailed description of your changes

## Code Style

### Python (main.py, watchdog.py)
- Follow PEP 8 style guide
- Use meaningful variable and function names
- Add docstrings to classes and complex functions
- Keep functions focused and under 50 lines when possible
- Use type hints where appropriate
- Comment complex logic, especially in PD controller and state machine

### JavaScript (script.js)
- Use async/await for Python API calls
- Keep functions pure and focused on single responsibility
- Use descriptive function names
- Add comments for non-obvious logic

### HTML/CSS (index.html, styles.css)
- Follow consistent indentation (2 or 4 spaces)
- Use semantic HTML elements
- Keep styling flat and consistent (Bloxstrap-inspired design)
- Avoid inline styles unless necessary

## Testing

Before submitting a pull request:
- **Test all changes** in actual Roblox environment
- Ensure the macro **runs without errors**
- Verify UI functionality works correctly
- Test with different timing parameters
- Check webhook notifications if modified
- Ensure no duplicate code or unused functions

## Reporting Issues

Use the GitHub issue tracker and include:
- **Clear description** of the problem
- **Steps to reproduce** the bug
- **Expected behavior** vs actual behavior
- **Error messages** and console logs
- **System information**: Python version, OS, Roblox client version

## Feature Requests

We welcome feature suggestions! Please:
- Check existing issues to avoid duplicates
- Provide detailed use case and expected behavior
- Explain why this feature would benefit users
- Consider implementation complexity

## Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Update README.md if adding new features
- Test thoroughly before submitting
- Respond to review feedback promptly
- Ensure code follows project style guidelines

## Development Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Make changes to source files in `src/` and `web/`
4. Test changes by running:
   ```bash
   python src\main.py
   ```

## Questions

For questions or help:
- Open a GitHub discussion
- Join our Discord server: https://discord.gg/87HgYm2APJ

Thank you for contributing! 🎣
