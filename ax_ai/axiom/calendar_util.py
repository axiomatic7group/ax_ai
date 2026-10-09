from calendar import HTMLCalendar, monthcalendar
from datetime import date
from datetime import date, datetime


class EventCalendar(HTMLCalendar):
    def __init__(self, events_by_date):
        super().__init__()
        # Expects a dictionary: {date(2026, 6, 15): [obj1, obj2]}
        self.events_by_date = events_by_date

    def formatday(self, day, weekday):
        """Renders a single day cell in the calendar table."""
        if day == 0:
            # Day 0 represents empty filler days at the start/end of a month
            return '<td class="noday">&nbsp;</td>'

        # Create a date object for the current cell
        # Note: self.year and self.month must be set when calling formatmonth
        current_date = date(self.year, self.month, day)
        
        # Get events for this day
        day_events = self.events_by_date.get(current_date, [])
        
        # Build the HTML block for the events
        events_html = ""
        for event in day_events:
            print("yes", event)
            events_html += f"""
                <div class="calendar-event">
                    <strong class="event-title">{event.project_name}</strong>
                    <p class="event-desc">{event.project_run_schedule}</p>
                </div>
            """

        # Return the complete HTML for the table cell
        return f"""
            <td class="calendar-day">
                <span class="day-number">{day}</span>
                <div class="day-events-container">{events_html}</div>
            </td>
        """

    def formatmonth(self, switched_year, switched_month, withyear=True):
        """Override to capture the year and month context safely."""
        self.year = switched_year
        self.month = switched_month
        return super().formatmonth(switched_year, switched_month, withyear=withyear)


class CustomGridCalendar:
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
                            <div class="calendar-task-item">
                                <a >
                                    <strong class="task-title">{event.project_name.project_name}</strong>
                                </a>
                                <p class="task-desc">{event.project_run_schedule}</p>
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


