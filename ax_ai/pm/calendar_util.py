from calendar import HTMLCalendar, monthcalendar
from datetime import date
from datetime import date, datetime


class ProjectGridCalendar:
    def __init__(self, events_by_datetime):
        # Your input dict has datetime keys; we normalize them to plain date objects here
        self.events_by_date = {}
        for dt_key, objects in events_by_datetime.items():
            # Handle both datetime and plain date objects safely
            normalized_date = dt_key.date() if isinstance(dt_key, datetime) else dt_key
            
            if normalized_date not in self.events_by_date:
                self.events_by_date[normalized_date] = []
            self.events_by_date[normalized_date].extend(objects)

    def render_month(self, year, month):
        """Builds the entire monthly grid layout using explicit loops."""
        month_matrix = monthcalendar(year, month)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        html = '<table class="calendar-month-grid">'
        
        # 1. Build Header Row
        html += '<thead><tr>'
        for name in day_names:
            html += f'<th>{name}</th>'
        html += '</tr></thead>'
        
        # 2. Build Body Rows
        html += '<tbody>'
        for week in month_matrix:
            html += '<tr>'
            for day in week:
                if day == 0:
                    html += '<td class="noday-cell">&nbsp;</td>'
                else:
                    current_date = date(year, month, day)
                    # Now this properly matches because keys are date objects
                    day_events = self.events_by_date.get(current_date, [])
                    
                    events_html = ""
                    for event in day_events:
                        events_html += f"""
                            <div class="calendar-task-item {event['task_status']}">
                                <a href="/cadence/projects/{event['task_project_name_link']}/{event['id']}"  class="{event['task_status']}">
                                    <strong class="task-title">{event['task_name']}</strong>
                                </a>
                                <p class="task-desc">{event['soft_due_date']}</p>
                            </div>
                        """


                    html += f"""
                        <td class="calendar-day-cell">
                            <div class="day-number-badge">{day}</div>
                            <div class="day-tasks-wrapper">{events_html}</div>
                        </td>
                    """
            html += '</tr>'
        
        html += '</tbody></table>'
        return html


