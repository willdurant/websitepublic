from django.shortcuts import render
from django.http import HttpRequest
import energy.plotting as pt
from energy.models import Energy
from bokeh.models import ColumnDataSource


# Create your views here.
def index(request: HttpRequest):
    if request.htmx:
        context, page = create_partial_context(request)
        return render(request, page, context)

    period_options = ["weeks", "days", "months", "years"]
    context = create_index_context(request)
    context["period_options"] = period_options
    context = add_card_context(context)
    return render(request, "index.html", context)


def add_card_context(context):
    gas, elec, total = create_recent_month_data()
    context["month_gas"] = gas
    context["month_elec"] = elec
    context["month_total"] = total
    context["month_gas_pc"] = round((gas / total) * 100, 0)
    context["month_elec_pc"] = round((elec / total) * 100, 0)

    return context


def create_index_context(request: HttpRequest) -> dict:
    scripts, divs = create_index_components(request)
    context = {
        "e_con_script": scripts[0],
        "e_con_div": divs[0],
        "e_cost_script": scripts[1],
        "e_cost_div": divs[1],
        "g_con_script": scripts[2],
        "g_con_div": divs[2],
        "g_cost_script": scripts[3],
        "g_cost_div": divs[3],
    }

    return context


def create_index_components(request: HttpRequest) -> tuple[list, list]:
    e_types = ["ELEC", "GAS"]
    variables = ["consumption", "cost"]

    scripts = []
    divs = []

    for e_type in e_types:
        for variable in variables:
            script, div = bokeh_visual(
                visual="bar", request=request, e_type=e_type, variable=variable
            )
            scripts.append(script)
            divs.append(div)

    return scripts, divs


def create_partial_context(request: HttpRequest) -> tuple[dict, str]:
    arguments = chart_options(request.headers["Hx-Trigger-Name"])
    script, div = bokeh_visual(
        visual=arguments["visual_type"],
        request=request,
        e_type=arguments["e_type"],
        variable=arguments["variable"],
    )
    context = {arguments["script"]: script, arguments["div"]: div}
    page = arguments["page"]

    return context, page


def chart_options(option: str) -> str:
    chart_options = {
        "e-con-period": {
            "e_type": "ELEC",
            "variable": "consumption",
            "page": "partials/bar-e-con.html",
            "script": "e_con_script",
            "div": "e_con_div",
            "visual_type": "bar",
        },
        "e-cost-period": {
            "e_type": "ELEC",
            "variable": "cost",
            "page": "partials/bar-e-cost.html",
            "script": "e_cost_script",
            "div": "e_cost_div",
            "visual_type": "bar",
        },
        "g-con-period": {
            "e_type": "GAS",
            "variable": "consumption",
            "page": "partials/bar-g-con.html",
            "script": "g_con_script",
            "div": "g_con_div",
            "visual_type": "bar",
        },
        "g-cost-period": {
            "e_type": "GAS",
            "variable": "cost",
            "page": "partials/bar-g-cost.html",
            "script": "g_cost_script",
            "div": "g_cost_div",
            "visual_type": "bar",
        },
        "all-period": {
            "e_type": "ALL",
            "variable": "all",
            "page": "partials/table-all.html",
            "script": "table_all_script",
            "div": "table_all_div",
            "visual_type": "table",
        },
    }

    return chart_options[option]


def bokeh_visual(visual: str, request: HttpRequest, e_type: str, variable: str):
    trigger, name = get_trigger(e_type, variable)
    data, chosen_period = create_bokeh_data(request, trigger, e_type)

    if visual == "bar":
        script, div = pt.vbar_components(
            data=data,
            e_type=e_type,
            title=f"{name} {variable} over time - {chosen_period}",
            y=variable,
            x_format="datetime",
        )
        return script, div

    if visual == "table":
        columns = ["date", "consumption", "cost", "days"]
        script, div = pt.table_component(data, columns)
        return script, div


def create_recent_month_data():
    data = pt.get_data(Energy, "months")
    gas = round(data.filter(energy_type="GAS").latest("start_date")["cost"] / 100, 2)
    elec = round(data.filter(energy_type="ELEC").latest("start_date")["cost"] / 100, 2)
    total = gas + elec

    return gas, elec, total


def create_bokeh_data(
    request: HttpRequest, trigger: str, e_type: str
) -> tuple[ColumnDataSource, str]:
    default_period = "weeks"
    chosen_period = request.GET.get(trigger, default_period)
    bokeh_dict = pt.get_dict(
        Energy, e_type, ["date", "consumption", "cost", "days"], chosen_period
    )
    bokeh_dict["cost"] = [round(cost / 100, 2) for cost in bokeh_dict["cost"]]
    data = ColumnDataSource(bokeh_dict)

    return data, chosen_period


def get_trigger(e_type: str, variable: str) -> tuple[str, str]:
    period_triggers = {
        "ELEC": {
            "consumption": "e-con-period",
            "cost": "e-cost-period",
            "name": "Electricity",
        },
        "GAS": {"consumption": "g-con-period", "cost": "g-cost-period", "name": "Gas"},
        "ALL": {"all": "all-period", "name": "All"},
    }

    trigger = period_triggers[e_type][variable]
    name = period_triggers[e_type]["name"]

    return trigger, name
