from bokeh.models.annotations import Legend
from requests.api import get
import sys
import os,csv,time,requests,math
from datetime import datetime
import matplotlib.pyplot as plt
import bokeh.plotting as bplt
import bokeh.models.tools as btools
from bokeh.models import Panel, Tabs
import bokeh.models.callbacks as bcall
from bokeh.resources import CDN
from bokeh.embed import components
from bokeh.layouts import row
from store import get_version,copy_index
from bokeh.palettes import viridis
from bokeh.transform import factor_cmap
from bokeh.resources import CDN
from bokeh.embed import file_html
from parser import create_summary,get_tests, get_warning_thorns, get_warning_type,test_comp,get_times,exceed_thresh,longest_tests,get_unrunnable,get_data,get_compile
import glob

records=os.listdir("./records")
curr_ver=get_version()-1
print(curr_ver)
curr=f"./records/version_{curr_ver}/build__2_1_{curr_ver}.log"
last=f"./records/version_{curr_ver-1}/build__2_1_{curr_ver-1}.log"

def gen_commits():
    '''
        This function generates a list of commits that have been made since the last run
        If the workflow was run manually it will say so.
    '''
    # This part of the code gets the list of commits and runs using the github api
    runs_list=requests.get("https://api.github.com/repos/mojamil/einsteintoolkit/actions/runs").json()
    commit_list=requests.get("https://api.github.com/repos/mojamil/einsteintoolkit/commits")
    response=commit_list.json()
    # Get the most recent commit
    try:
        current=response[0]["sha"]
    except:
        out="<th>"
        message="Manual Run"
        try:
            date=runs_list["workflow_runs"][0]["created_at"]
        except:
            date="Unavailable"
        out+="Commit 1 </th>"
        out+="<tr> <td> Date: </td> <td>"+date+"</td> </tr> \n"
        out+="<tr> <td> Message: </td> <td> Could not receive commit message due to rate limits</td> </tr> \n"
        return out

    # Get the commit associated with the last run
    previous=runs_list["workflow_runs"][1]["head_commit"]['id']

    # Compare the current commit with the one from the previous runn
    compare=requests.get(f"https://api.github.com/repos/mojamil/einsteintoolkit/compare/{previous}...{current}")
    commits=compare.json()["commits"]

    # Create table listing a manual run or a list of commits
    out="<th>"
    count=1
    if previous==current:
        message="Manual Run"
        date=runs_list["workflow_runs"][0]["created_at"]
        out+="Commit "+str(count)+"</th>"
        out+="<tr> <td> Date: </td> <td>"+date+"</td> </tr> \n"
        out+="<tr> <td> Message: </td> <td>"+message+"</td> </tr> \n"

    for commit in commits:
        message=commit["commit"]["message"]
        message=message.replace("\n\n","\n")
        message=message.replace('\n','<br>')
        date=commit["commit"]["author"]["date"]
        out+="Commit "+str(count)+"</th>"
        out+="<tr> <td> Date: </td> <td>"+date+"</td> </tr> \n"
        out+="<tr> <td> Message: </td> <td>"+message+"</td> </tr> \n"
        count+=1
    return out

# log_link=f"https://github.com/mojamil/einsteintoolkit/blob/master/records/version_{last_ver}/{last[ext-1:]+str(last_ver+1)}"
def gen_diffs(readfile):
    '''
        This function generates the html table that shows
        the comparison of test logs from last version generated
        by test_comp
    '''

    # The test_comp function provides tests that failed, were newly added or newly removed
    test_comparison=test_comp(readfile,last)
    print(test_comparison)

    # Setup the header for the table
    output='''<table class="table table-bordered " >
    <caption style="text-align:center;font-weight: bold;caption-side:top">Failed Tests and Changes</caption>
    <tr><th></th><th>logs(1_process)</th><th>logs(2_processes)</th><th>diffs(1_process)</th><th>diffs(2_processes)</th></tr>\n'''

    for result in test_comparison.keys():
        # For each test make a header with the description of why that test is being shown(failed, newly added, newly failing)
        output+=f'''<tr><th colspan="5">'''+result+"</th></tr>\n"

        # If no such test exists add empty row
        if(len(test_comparison[result])==0):
            output+="<tr><td></td></tr>"

        # For each test get the thorn name and the current version
        for test in test_comparison[result]:
            thorn=test.split()[-1]
            thorn=thorn[:len(thorn)-1]
            test_name=test.split()[0]
            ver=curr_ver

            # Since the removed test would have been stored in the curr version subtract 1 from the version number
            if("Removed" in result):
                ver-=1

            # Links for logs and diffs of the tests in the test_comparison dictionary based on the number of procs
            logl1=f"https://github.com/mojamil/einsteintoolkit/tree/gh-pages/records/version_{ver}/sim_{ver}_1/{thorn}/{test_name}.log"
            logl2=f"https://github.com/mojamil/einsteintoolkit/tree/gh-pages/records/version_{ver}/sim_{ver}_2/{thorn}/{test_name}.log"
            diffl1=f"https://github.com/mojamil/einsteintoolkit/tree/gh-pages/records/version_{ver}/sim_{ver}_1/{thorn}/{test_name}.diffs"
            diffl2=f"https://github.com/mojamil/einsteintoolkit/tree/gh-pages/records/version_{ver}/sim_{ver}_2/{thorn}/{test_name}.diffs"

            # Check if these files are available if not display not avaible on the table 
            if(os.path.isfile("./"+logl1[logl1.find("records"):])):
                output+=f"  <tr><td>{test}</td><td><a href='{logl1}'>log</a></td>"
            else:
                output+=f" <tr><td>{test}</td><td>Not Available</td>"
            if(os.path.isfile("./"+logl2[logl2.find("records"):])):
                output+=f"  <td><a href='{logl2}'>log</a></td>"
            else:
                output+=f" <td>Not Available</td>"
            if(os.path.isfile("./"+diffl1[diffl1.find("records"):])):
                output+=f"<td><a href='{diffl1}'>diff</a></td>"
            else:
                output+=f"<td>Not Available</td>"  
            if(os.path.isfile("./"+diffl2[diffl2.find("records"):])):
                output+=f"<td><a href='{diffl2}'>diff</a></td></tr>\n"
            else:
                output+=f"<td>Not Available</td></tr>\n"  
    
    output+="</table>"
    return output


def gen_time(readfile):
    '''
        This function generates a table with the tests that took the longest time
    '''
    # The get_times function parses the data from the log files
    time_dict=get_times(readfile)

    # This part creates html table contianing the top 10 longest tests
    output='''<table class="table table-bordered " >
    <caption style="text-align:center;font-weight: bold;caption-side:top">Longest Tests</caption>\n'''
    output+="<tr><th>Test Name</th><th>Running Time</th>"
    for times in longest_tests(time_dict,10).keys():
        output+=f"   <tr><td>{times}</td><td>{time_dict[times]}s</td></tr>\n"
    output+="</table><br>"
    return output

def plot_test_data(readfile):

    # Get dataa from the csv and create lists for each field
    runnable=list(get_data("Runnable tests").values())
    times=list(get_data("Number of tests passed").keys())
    passed=list(get_data("Number of tests passed").values())
    time_taken=list(get_data("Time Taken").values())
    compile_warn=list((get_data("Compile Time Warnings").values()))

    # Get the of dictionary of thorns with their warning counts
    warning_thorns=get_warning_thorns(readfile)

    # Turn that dictionary into lists so you can pick the thorns with most warnings
    counts=list(warning_thorns.values())
    counts_trunc=sorted(counts,reverse=True)[:7]
    warning_types_trunc=[]
    warning_types_list=list(warning_thorns.keys())

    for count in counts_trunc:
        i=counts.index(count)
        warning_types_trunc.append(warning_types_list[i])
        warning_types_list.pop(i)
        counts.pop(i)
    counts=counts_trunc
    warning_types_list=warning_types_trunc

    # The python library bokeh has a special data structure called a column data source that functions similarly to a dictionary
    src=bplt.ColumnDataSource(data=dict(
        t=times,
        rt=runnable,
        tp=passed,
        timet=time_taken,
        cmt=compile_warn,
        xax=[0]*len(times),
        url=[f"./index_{x+1}.html" for x in range(0,curr_ver)],
    ))

    TOOLTIPS = [
        ("Tests Passed", "$tp"),
    ]
    print(src.data["rt"])

    # p is the first figure an area chart with the number of tests passed out of the ones ran
    # Tools attribute gives ways to manipulate the plot such as having clickable points, scrool to zoom and pan to zoom.
    # The rest of the attributes should be self explanatory
    p=bplt.figure(x_range=times,y_range=(max(0,min(runnable)-30),max(runnable)+10),plot_width=1000, plot_height=600,tools="tap,wheel_zoom,box_zoom,reset",
           y_axis_label="Number of Tests", x_axis_label="Date",
           title="Passed Tests", toolbar_location="below",sizing_mode='scale_width')
    
    # Circles are points on the graph
    p.circle(times,runnable,size=10,color="green",legend_label="Runnable Tests")
    p.circle('t','tp',size=10,color="blue",source=src,legend_label="Number of Tests Passed")

    # The taptool helps have these points link to the previous builds
    url = "@url"
    taptool = p.select(type=btools.TapTool)
    taptool.callback = bcall.OpenURL(url=url)

    # This part fills in the area below the points
    p.varea(y1='rt',y2='xax', x='t', color="green",source=src,alpha=0.5)
    p.varea(y1='tp',y2='xax', x='t', color="blue",source=src,alpha=0.5)

    

    # The graphs are displayed in a tabs and this part sets that up
    tab1 = Panel(child=p, title="Test Results")
    p.legend.location = "top_left"

    # This graph is for how long the testing part takes uses similar code to the first one but instead of area it has lines connecting points
    p1=bplt.figure(x_range=times,y_range=(0,max(time_taken)+5),plot_width=1000, plot_height=600,tools="tap,wheel_zoom,box_zoom,reset",
           y_axis_label="Time(minutes)", x_axis_label="Date",
           title="Time Taken for Tests", toolbar_location="below",sizing_mode='scale_width')
    p1.circle('t','timet',size=10,color="blue",source=src)
    p1.line('t','timet',color="blue",source=src)
    taptool = p1.select(type=btools.TapTool)
    taptool.callback = bcall.OpenURL(url=url)
    tab2 = Panel(child=p1, title="Time Taken")


    # This graph is for the total number of compilation warnings and it uses the same code as the above plot but with different data
    p2=bplt.figure(x_range=times,y_range=(0,max(compile_warn)+50),plot_width=1000, plot_height=600,tools="tap,wheel_zoom,box_zoom,reset",
           title="Compilation Warnings",y_axis_label="Number of Compilation Warnings", x_axis_label="Date",
           toolbar_location="below",sizing_mode='scale_width')
    p2.circle('t','cmt',size=10,color="blue",source=src)
    p2.line('t','cmt',color="blue",source=src)
    taptool = p2.select(type=btools.TapTool)
    taptool.callback = bcall.OpenURL(url=url)
    tab3 = Panel(child=p2, title="Compile Time Warnings")

    src1=bplt.ColumnDataSource(data=dict(cts=counts,
        wts=warning_types_list))

    # This plot is a bar graph showing the top 7 thorns with the most warnings
    p3=bplt.figure(x_range=warning_types_list,plot_width=1200, title="Compilation Warning Thorns",
           y_axis_label="Number of Warnings", x_axis_label="Name of Thorn",
           toolbar_location="below", tools="tap,wheel_zoom,box_zoom,reset",sizing_mode='scale_width')
    p3.vbar(x='wts', top='cts', width=0.9, source=src1,
       line_color='white', fill_color=factor_cmap('wts', palette=viridis(len(counts)), factors=warning_types_list))
    tab4=Panel(child=p3, title="Compilation Warning Thorns")

    p.xaxis.major_label_orientation = math.pi/6
    p1.xaxis.major_label_orientation = math.pi/6
    p2.xaxis.major_label_orientation = math.pi/6


    # Bokeh createst the html script and javscript for the plots using this code
    html = file_html(Tabs(tabs=[tab1, tab2,tab3]), CDN, "Plots")
    with open("./docs/plot.html","w") as fp:
        fp.write(html)
    #script, div = components(Tabs(tabs=[tab1, tab2,tab3]))
    script, div=components(p3)
    return script,div


def gen_unrunnable(readfile):
    '''
        This function generates a html showing which tests could not be run and the reason
    '''
    m,n=get_unrunnable(readfile)
    output=''' <table class="table table-bordered " >
    <caption style="text-align:center;font-weight: bold;caption-side:top">Unrunnable Tests</caption>\n'''
    output+="<tr><th>Tests Missed for Lack Of Thorns</th><th>Missing Thorns</th></tr>\n"
    for test in m.keys():
        thorns=','.join(m[test])
        output+=f"  <tr><td>{test}</td><td>{thorns}</td></tr>\n"
    output+="<tr><th>Tests missed for different number of processors required:</th><th>Processors Required</th></tr>\n"
    for test in n.keys():
        output+=f"  <tr><td>{test}</td><td>{n[test]}</td></tr>\n"
    output+="</table>"
    return output

def summary_to_html(readfile,writefile):
    '''
        This function reads the log file and outputs and html
        page with the summary in a table
    '''

    data=create_summary(readfile)
    
    contents=""
    script,div=plot_test_data(readfile)


    # Check Status Using the data from the summary
    status="All Tests Passed"
    if data["Number of tests passed"]==0:
        status="All Tests Passed"
    elif data["Number failed"]!=0:
        status="Some Tests Failed"
        # Send email if tests failed
        #os.system(f'python3 mail.py')
    with open(writefile,"w") as fp:
        for key in data.keys():

            # Add a table row for each data field
            contents+=f"        <tr><th>{key}</th><td>{data[key]}</td><tr>\n"

        # The formatted string holds the html template and loads in the values for content and status    
        template=f'''<!doctype html>
    <html lang="en">
        <head>
            <title>Summary of Tests</title>
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
            <style>
            .bk-root .bk {{
                margin: 0 auto !important;
            }}
            </style>
            <style>
            .sidebar {{
                height: 100%; 
                width: 150px;
                position: fixed;
                z-index: 1; 
                top: 0; 
                left: 0;
                background-color: #212529; 
                overflow-x: hidden;
                padding-top: 20px; 
            }}
            .sidebar a {{
                padding: 6px 8px 6px 16px;
                text-decoration: none;
                font-size: 18px;
                color: #dbdcdd;
                display: block;
                }}
            .sidebar a:hover {{
                color: white;
            }}
            .container{{
              padding-left: 150px;
              font-size: 18px;
            }}
                        /* On screens that are less than 700px wide, make the sidebar into a topbar */
            @media screen and (max-width: 500px) {{
            .sidebar {{
              display: none;
            }}
            .container {{
              padding-left:0px;
            }}
            }}
            </style>
            <script src="https://cdn.bokeh.org/bokeh/release/bokeh-2.0.1.min.js"
            crossorigin="anonymous"></script>
            {script}

        </head>
        <body>
            <div class="sidebar">
            </div>
            <script src='version.js'>
            </script>
            <div class="container">
                <h1 style="text-align:center">{status}</h1>
                <h3 style="text-align:center"><a href="https://github.com/mojamil/einsteintoolkit/tree/gh-pages/records/version_{curr_ver}">Build #{curr_ver}</a></h3>
                <table class="table table-bordered " >
                <caption style="text-align:center;font-weight: bold;caption-side:top">Summary</caption>
                {contents}
                </table>
                <br>
                <table class="table table-bordered " >
                <caption style="text-align:center;font-weight: bold;caption-side:top">Commits in Last Push</caption>
                {gen_commits()}
                </table>
                {gen_diffs(readfile)}
                <br>
                {gen_time(readfile)}
                <br>
                {gen_unrunnable(readfile)}
                <br>
                <table style="margin: 0 auto;">
                    <iframe src="plot.html" height="700" width="1100"></iframe>
                </table>
                <table style="margin: 0 auto;">
                    {div}
                </table>
            <div>
            
        </body>
    </html>
        '''
        fp.write(template)

def write_to_csv(readfile):
    '''
        This function is used to store data between builds into a csv
    '''

    total=sum(x[1] for x in get_times(readfile).items())

    data=create_summary(readfile)
    data["Time Taken"]=total/60
    local_time = datetime.today().strftime('%Y-%m-%d')
    local_time+=f"({curr_ver})"
    data["Compile Time Warnings"]=get_compile(f"records/version_{curr_ver}/build_{curr_ver}.log")
    with open('test_nums.csv','a') as csvfile:
        contents=f"{local_time}"
        for key in data.keys():
            contents+=f",{data[key]}"
        contents+="\n"
        csvfile.write(contents)



if __name__ == "__main__":
    write_to_csv(curr)
    summary_to_html("./records/version_9/build__2_1_9.log","docs/index_9.html")
    copy_index(get_version()-1)


