#!/bin/sh


. /usr/lib/libmodcgi.sh

if [ "$sec_level" -gt 0 ]; then
	cgi --id=rudishell
	cgi_begin "$(lang de:"Rudi(ment&auml;r)-Shell" en:"Rudi(mentary) Shell")"
	print_warning "$(lang \
	  de:"Rudi-Shell ist in der aktuellen Sicherheitsstufe nicht verf&uuml;gbar!" \
	  en:"Rudi shell is not available at the current security level!" \
	)"
	cgi_end
	exit
fi

cgi --id=rudishell
cgi_begin "$(lang de:"Rudi(ment&auml;r)-Shell" en:"Rudi(mentary) Shell")"
cat << EOF
	<style>
		.shell-row { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; }
		.shell-row input[type='text'] { flex: 1 1 auto; min-width: 0; width: auto !important; }
		.shell-row input[type='submit'], .shell-row input[type='button'] { flex: 0 0 auto; white-space: nowrap; }
		#shell_output {
			margin-top: 10px;
			padding: 10px 12px;
			border: 1px solid #97a6b7;
			border-radius: 6px;
			background: #f3f7fb;
			min-height: 120px;
			max-height: 45vh;
			overflow: auto;
			line-height: 1.35;
			white-space: pre-wrap;
			word-break: break-word;
		}
		#shell_busy {
			position: fixed;
			right: 10px;
			top: 10px;
			z-index: 10001;
			padding: 6px 10px;
			border-radius: 14px;
			background: rgba(16, 48, 88, 0.9);
			color: #ffffff;
			font-size: 12px;
			box-shadow: 0 2px 10px rgba(0,0,0,0.25);
			display: none;
		}
		@media (max-width: 600px) {
			.textwrapper, .textwrapper textarea { width: 100%; box-sizing: border-box; }
			textarea#script_code { width: 100% !important; }
			table, tbody, tr, td, form { display: block; width: 100%; box-sizing: border-box; }
			input[type='text'], input[type='file'] { width: 100%; max-width: 100%; box-sizing: border-box; }
			input[type='button'], input[type='submit'] { margin: 2px 0; }
			.shell-row { gap: 6px; }
			.shell-row input[type='text'] { width: auto !important; }
		}
	</style>
	<script type="text/javascript">
		var editing=0,code,output,exec,tar,gz,dl,his,repeat,file,busy,hist = Array();
		window.onload = function(){
			code = document.getElementById("script_code");
			output = document.getElementById("shell_output");
			exec = document.getElementById("exec");
			tar = document.getElementById("tar");
			gz = document.getElementById("gz");
			dl = document.getElementById("dl");
			his = document.getElementById("history");
			file = document.getElementById("file2edit");
			repeat = document.getElementById("repeat");
			busy = document.getElementById("shell_busy");
		}
		function busyStart(msg) {
			if (busy) {
				busy.innerHTML = "⌛ " + (msg || "$(lang de:"Bitte warten..." en:"Working...")");
				busy.style.display = "block";
			}
			if (exec) exec.disabled = true;
		}
		function busyStop() {
			if (busy) busy.style.display = "none";
			if (exec) exec.disabled = false;
		}
		function setShellOutput() {
			hist.push(new Array(code.value, output.innerHTML));
			his[hist.length - 1] = new Option("#" + (hist.length - 1));
			his.selectedIndex = 0;
		}
		function historySelected(index) {
			code.value = hist[hist.length - 1 - index][0];
			output.innerHTML = hist[hist.length - 1 - index][1];
		}
		function cleanHistory() {
			while (his.length > 0)
				his.remove(0)
		}
		function ajax_exec(params){
			var ajax = new XMLHttpRequest();
			ajax.open("POST","/cgi-bin/shell/cmd.cgi?pid=$$",false);
			ajax.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
			ajax.setRequestHeader("Content-length", params.length);
			ajax.setRequestHeader("Connection", "close");
			ajax.send(params);
			return ajax.responseText;
		}
		function RudiEdit() {
			busyStart("$(lang de:"Lade Datei..." en:"Loading file...")");
			window.setTimeout(function () {
				output.innerHTML=ajax_exec("script=cat "+file.value);
				code.value=output.firstChild ? output.firstChild.nodeValue : "";
				exec.value="$(lang de:"Editieren" en:"Edit")";
				editing=1;
				busyStop();
			}, 0);
		}
		function tx(){
			if(repeat.value != ""){
				setTimeout("tx();",repeat.value);
			}
			busyStart(editing ? "$(lang de:"Speichere..." en:"Saving...")" : "$(lang de:"F&uuml;hre Skript aus..." en:"Running script...")");
			window.setTimeout(function () {
				if(editing){
					ajax_exec('script=echo "'+encodeURIComponent(code.value)+'" > '+file.value);
					code.value="";
					output.innerHTML="$(lang de:"Editiert!" en:"Edited!")";
					exec.value="$(lang de:"Skript ausf&uuml;hren" en:"Run script")";
					editing=0;
					busyStop();
				}
				else{
					if(dl.checked){
						window.location = "/cgi-bin/shell/cmd.cgi?pid=$$&dl=true&script="+encodeURIComponent(code.value)+"&tar="+tar.checked+"&gz="+gz.checked;
						busyStop();
					}
					else{
						output.innerHTML=ajax_exec("script="+encodeURIComponent(code.value));
						setShellOutput();
						busyStop();
					}
				}
			}, 0);
		}
	</script>
	<br>
	<div id="shell_busy">⌛ $(lang de:"Bitte warten..." en:"Working...")</div>
	<div class="textwrapper"><textarea id="script_code" rows="10" cols="80" style="width:100%;box-sizing:border-box;max-width:100%"></textarea></div><p>
	<input type="button" id="exec" value="$(lang de:"Skript ausf&uuml;hren" en:"Run script")" onClick="tx();">&nbsp;&nbsp;
	<label for="repeat">$(lang de:"Wiederholungsintervall" en:"Loop interval")</label> <input type="text" id="repeat" size=6>&nbsp;ms&nbsp;&nbsp;
	<label for="history">$(lang de:"Historie" en:"History")</label> <select id="history" onChange="historySelected(this.selectedIndex)"></select>
	<input type="button" value="$(lang de:"Hist. l&ouml;schen" en:"Delete hist.")" onClick="cleanHistory()">&nbsp;&nbsp;
	<input type="checkbox" id="dl"><label for="dl">Download</label>
	(<input type="checkbox" id="tar"><label for="tar">.tar</label>
	<input type="checkbox" id="gz"><label for="gz">.gz</label> )
	<table>
		<form action="/cgi-bin/shell/upload.cgi?pid=$$" target="upload" method="POST" enctype="multipart/form-data">
			<tr><td><label for="source">$(lang de:"Quelldatei" en:"Source file")</label></td><td><input type="file" name="source" id="source" size=50></td></tr>
			<tr><td><label for="target">$(lang de:"Zieldatei" en:"Target file")</label></td><td><div class="shell-row"><input type="text" name="target" id="target" value="/var/tmp/rudi_upload" size=50 style="box-sizing:border-box"><input type="submit" value="$(lang de:"Hochladen" en:"Upload")"></div></td></tr>
		</form>
		<tr><td><label for="file2edit">$(lang de:"Rudi-Edit" en:"Rudi edit")</label></td><td><div class="shell-row"><input type="text" id="file2edit" value="/var/tmp/tmp.txt" size=50 style="box-sizing:border-box"><input type="button" value="$(lang de:"Datei editieren" en:"Edit file")" onClick="RudiEdit()"></div></td></tr>
	</table>
	<iframe name="upload" style="width: 0; height: 0; visibility: hidden;"></iframe>
	<pre id="shell_output">---</pre>
EOF
cgi_end
echo $$ > /var/run/rudi_shell.pid

