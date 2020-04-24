#!/usr/bin/python

from datetime import date
import gviz_api

page_template = """
<html>
  <head>
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
      google.charts.load('current', {'packages':['timeline']});
      google.charts.setOnLoadCallback(drawChart);
      function drawChart() {
        var container = document.getElementById('timeline');
        var chart = new google.visualization.Timeline(container);
        var dataTable = new google.visualization.DataTable(%s);
        chart.draw(dataTable);
      }
    </script>
  </head>
  <body>
    <div id="timeline" style="height: %ipx;"></div>
  </body>
</html>
"""


def export_html(data, file, height: int = 300):
    schema = {
        "machine_id": ("string", "Machine"),
        "label": ("string", "Label"),
        "start": ("date", "Start"),
        "end": ("date", "End"),
    }

    data_table = gviz_api.DataTable(schema)
    data_table.LoadData(data)

    # Create a JSON string.
    json = data_table.ToJSon(columns_order=("machine_id", "label", "start", "end"))

    with open(file, "w") as html:
        html.write(page_template % (json, height))


def main():
    # Creating the data
    data = [
        {
            "machine_id": "M1",
            "label": "label 1",
            "start": date(2009, 11, 2),
            "end": date(2011, 1, 2),
        },
        {
            "machine_id": "M2",
            "label": "label 2",
            "start": date(2009, 3, 1),
            "end": date(2012, 4, 2),
        },
        {
            "machine_id": "M3",
            "label": "label 3",
            "start": date(2012, 3, 1),
            "end": date(2012, 4, 2),
        },
    ]
    export_html(data)


if __name__ == "__main__":
    main()
