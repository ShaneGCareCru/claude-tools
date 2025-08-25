"""
Report templates for TechFlow test framework.
"""

from typing import Dict, Any


class ReportTemplates:
    """Templates for generating various report formats."""
    
    def render_html_template(self, context: Dict[str, Any]) -> str:
        """Render HTML report template."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TechFlow Test Report - {context['run_id']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 1.1em;
            margin-top: 10px;
        }}
        .content {{
            padding: 30px;
        }}
        .status-card {{
            background: {'#d4edda' if context['success'] else '#f8d7da'};
            border: 1px solid {'#c3e6cb' if context['success'] else '#f5c6cb'};
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .status-card h2 {{
            color: {'#155724' if context['success'] else '#721c24'};
            margin: 0 0 10px 0;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        .metric h3 {{
            margin: 0 0 10px 0;
            color: #495057;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .metric .value {{
            font-size: 2em;
            font-weight: bold;
            color: #343a40;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #343a40;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .artifacts, .failures {{
            list-style: none;
            padding: 0;
        }}
        .artifacts li, .failures li {{
            background: #f8f9fa;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
        }}
        .failures li {{
            border-left-color: #dc3545;
        }}
        .recommendations {{
            background: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 8px;
            padding: 20px;
        }}
        .recommendations h3 {{
            color: #856404;
            margin-top: 0;
        }}
        .recommendations ul {{
            margin-bottom: 0;
        }}
        .quality-score {{
            display: inline-block;
            background: {context['quality_assessment']['color']};
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TechFlow Test Report</h1>
            <div class="subtitle">Run ID: {context['run_id']} | {context['timestamp']}</div>
        </div>
        
        <div class="content">
            <div class="status-card">
                <h2>{'✅ TEST PASSED' if context['success'] else '❌ TEST FAILED'}</h2>
                <p>Quality Score: <span class="quality-score">{context['quality_score']:.1f}/5.0 ({context['quality_assessment']['grade']})</span></p>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <h3>Duration</h3>
                    <div class="value">{context['duration']}</div>
                </div>
                <div class="metric">
                    <h3>Retries</h3>
                    <div class="value">{context['retry_count']}</div>
                </div>
                <div class="metric">
                    <h3>Artifacts</h3>
                    <div class="value">{len(context['artifacts'])}</div>
                </div>
                <div class="metric">
                    <h3>Failures</h3>
                    <div class="value">{context['failure_count']}</div>
                </div>
            </div>
            
            {self._render_artifacts_section(context['artifacts']) if context['artifacts'] else ''}
            
            {self._render_failures_section(context['failures']) if context['failures'] else ''}
            
            <div class="section">
                <h2>Configuration</h2>
                <ul>
                    <li><strong>CLI Path:</strong> {context['config']['cli_path']}</li>
                    <li><strong>Branch Strategy:</strong> {context['config']['branch_strategy']}</li>
                    <li><strong>Timeout:</strong> {context['config']['timeout']}</li>
                    <li><strong>Max Retries:</strong> {context['config']['max_retries']}</li>
                </ul>
            </div>
            
            <div class="recommendations">
                <h3>📋 Recommendations</h3>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in context['recommendations'])}
                </ul>
            </div>
        </div>
    </div>
</body>
</html>"""

    def _render_artifacts_section(self, artifacts) -> str:
        """Render artifacts section for HTML."""
        if not artifacts:
            return ""
        
        artifact_items = ""
        for artifact in artifacts:
            url_link = f'<a href="{artifact["url"]}" target="_blank">View</a>' if artifact['url'] else 'No URL'
            artifact_items += f"""
                <li>
                    <strong>{artifact['type']}:</strong> {artifact['identifier']} 
                    <small>({artifact['created']})</small> - {url_link}
                </li>
            """
        
        return f"""
            <div class="section">
                <h2>🎯 Artifacts Created</h2>
                <ul class="artifacts">
                    {artifact_items}
                </ul>
            </div>
        """
    
    def _render_failures_section(self, failures) -> str:
        """Render failures section for HTML."""
        if not failures:
            return ""
        
        failure_items = ""
        for failure in failures:
            failure_items += f"""
                <li>
                    <strong>{failure['stage']} - {failure['type']}</strong><br>
                    {failure['message']}
                    {f'<br><small>{failure["details"]}</small>' if failure['details'] else ''}
                    <small style="float: right; opacity: 0.7;">{failure['timestamp']}</small>
                </li>
            """
        
        return f"""
            <div class="section">
                <h2>❌ Failures</h2>
                <ul class="failures">
                    {failure_items}
                </ul>
            </div>
        """
    
    def render_markdown_template(self, context: Dict[str, Any]) -> str:
        """Render Markdown report template."""
        status_emoji = "✅" if context['success'] else "❌"
        status_text = "PASSED" if context['success'] else "FAILED"
        
        md_content = f"""# TechFlow Test Report

**Run ID:** {context['run_id']}  
**Timestamp:** {context['timestamp']}  
**Status:** {status_emoji} {status_text}  
**Quality Score:** {context['quality_score']:.1f}/5.0 ({context['quality_assessment']['grade']})

## 📊 Metrics

| Metric | Value |
|--------|-------|
| Duration | {context['duration']} |
| Retries | {context['retry_count']} |
| Artifacts | {len(context['artifacts'])} |
| Failures | {context['failure_count']} |

"""
        
        # Add artifacts section
        if context['artifacts']:
            md_content += "## 🎯 Artifacts Created\n\n"
            for artifact in context['artifacts']:
                url_text = f"[View]({artifact['url']})" if artifact['url'] else "No URL"
                md_content += f"- **{artifact['type']}:** {artifact['identifier']} ({artifact['created']}) - {url_text}\n"
            md_content += "\n"
        
        # Add failures section
        if context['failures']:
            md_content += "## ❌ Failures\n\n"
            for failure in context['failures']:
                md_content += f"### {failure['stage']} - {failure['type']}\n\n"
                md_content += f"**Message:** {failure['message']}\n\n"
                if failure['details']:
                    md_content += f"**Details:** {failure['details']}\n\n"
                md_content += f"**Time:** {failure['timestamp']}\n\n"
        
        # Add configuration
        md_content += f"""## ⚙️ Configuration

- **CLI Path:** {context['config']['cli_path']}
- **Branch Strategy:** {context['config']['branch_strategy']}
- **Timeout:** {context['config']['timeout']}
- **Max Retries:** {context['config']['max_retries']}

## 📋 Recommendations

"""
        
        for rec in context['recommendations']:
            md_content += f"- {rec}\n"
        
        md_content += f"""
---
*Report generated by TechFlow Test Framework*
"""
        
        return md_content