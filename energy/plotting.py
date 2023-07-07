from django.db.models import Sum, ExpressionWrapper, DateTimeField, Count, Min
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from bokeh.models import (
    HoverTool,
    DataTable,
    DateFormatter,
    TableColumn,
)
from bokeh.embed import components
from bokeh.models import Div
from bokeh.layouts import layout
from bokeh.plotting import figure, curdoc
from datetime import timedelta, datetime


def get_period(model, time_period):
    if time_period == "weeks":
        usage = model.objects.annotate(
            start_date=ExpressionWrapper(
                TruncWeek("date"), output_field=DateTimeField()
            )
        )
    elif time_period == "months":
        usage = model.objects.annotate(
            start_date=ExpressionWrapper(
                TruncMonth("date"),
                output_field=DateTimeField(),
            )
        )
    elif time_period == "years":
        usage = model.objects.annotate(
            start_date=ExpressionWrapper(
                TruncYear("date"),
                output_field=DateTimeField(),
            )
        )
    else:
        usage = model.objects.annotate(
            start_date=ExpressionWrapper(TruncDay("date"), output_field=DateTimeField())
        )

    return usage


def get_data(model, time_period):
    usage = get_period(model, time_period)

    usage = (
        usage.values("start_date")
        .annotate(
            min_date=Min("date"),
            consumption=Sum("consumption"),
            cost=Sum("cost"),
            days=Count("date", distinct=True),
        )
        .order_by("start_date")
    )

    return usage


def get_column(data, energy_type, column_name):
    if energy_type == "ALL":
        column = [x[column_name] for x in list(data.values(column_name))]
        return column

    column = [
        x[column_name]
        for x in list(data.filter(energy_type=energy_type).values(column_name))
    ]

    return column


def get_dict(model, energy_type, columns, time_period) -> dict:
    data = get_data(model, time_period)
    bokeh_dict = {column: get_column(data, energy_type, column) for column in columns}
    bokeh_dict["date"] = [
        datetime.combine(date, datetime.min.time())
        for date in get_column(data, energy_type, "min_date")
    ]
    width = get_column(data, energy_type, "days")
    bokeh_dict["width"] = [timedelta(days=days) for days in width]
    bokeh_dict["xdate"] = [
        date + timedelta(days=days / 2) for date, days in zip(bokeh_dict["date"], width)
    ]
    return bokeh_dict


def get_hovertool(x, y, z, x_format=None):
    x_tag = "@" + x
    y_tag = "@" + y
    z_tag = "@" + z

    if x_format == "datetime":
        x_tag = x_tag + "{%F}"
        formatters = {
            "@" + x: x_format,
        }
        tooltips = [(x, x_tag), (y, y_tag), (z, z_tag)]
        hovertool = HoverTool(
            tooltips=tooltips,
            formatters=formatters,
        )
        return hovertool

    tooltips = [(x, x_tag), (y, y_tag), (z, z_tag)]
    hovertool = HoverTool(
        tooltips=tooltips,
    )
    return hovertool


def vbar_components(data, e_type, title, y, x="date", x_format=None):
    fig = figure(
        width=400, height=400, title=title, x_axis_type=x_format, toolbar_location=None
    )

    doc = curdoc()
    doc.theme = "dark_minimal"
    doc.add_root(fig)

    if x == "date":
        x = "xdate"

    fill_color, line_color = get_colours(e_type)

    fig.vbar(
        source=data,
        x=x,
        top=y,
        width="width",
        fill_color=fill_color,
        line_color=line_color,
    )

    if x == "xdate":
        x = "date"

    hovertool = get_hovertool(x, y, "days", x_format)

    fig.add_tools(hovertool)

    fig.border_fill_color = "#212529"

    script, div = components(fig)

    return script, div


def get_colours(e_type: str) -> tuple[str, str]:
    colours = {
        "ELEC": {"fill": "salmon", "line": "lightsalmon"},
        "GAS": {"fill": "blue", "line": "lightblue"},
    }

    return colours[e_type]["fill"], colours[e_type]["line"]


def table_component(data, columns: list[str]):
    table_columns = [
        TableColumn(field="date", title="Date", formatter=DateFormatter())
        if column == "date"
        else TableColumn(field=column, title=column.title())
        for column in columns
    ]

    data_table = DataTable(
        source=data,
        columns=table_columns,
        width=400,
        height=280,
    )

    data_table.background = "#212529"

    script, div = components(data_table)

    return script, div
