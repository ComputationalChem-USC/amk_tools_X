import bokeh.plotting
import bokeh.palettes
import bokeh.models as bkm
import bokeh.transform
import bokeh.layouts
import bokeh.core.properties
import argparse
import sys
from string import Template
import RXReader as arx
import amk_assets
import html
import json
import networkx as nx
import numpy as np
import copy


### AutoMeKin-X visual identity: white surfaces, black text, blue accents and rules ("plecas").
### Edit these to re-theme the generated HTML without touching the plotting/layout logic below.
amk_palette = {
	"accent": "#1d4ed8",          # blue -- primary accent (rules, links, active controls)
	"accentHover": "#1e40af",
	"accentSoft": "rgba(29, 78, 216, 0.08)",
	"highlight": "#2563eb",       # blue -- selection / highlighted path
	"highlightInk": "#1d4ed8",    # blue, for TS labels on white
	"surface": "#ffffff",
	"surfaceAlt": "#f8fafc",
	"pageBackground": "#ffffff",
	"border": "#e2e8f0",
	"textPrimary": "#0b0f19",     # near-black text
	"textSecondary": "#334155",
	"textMuted": "#64748b",
	"fontDisplay": "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
	"fontBody": "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
	# Sequential ramp (light -> dark blue) for the energy-mapped node colors
	"nodeEnergyRamp": ["#eff6ff", "#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa",
					   "#3b82f6", "#2563eb", "#1d4ed8", "#1e3a8a"],
	# Categorical colors for energy profiles (one per path): blues, black and greys
	"profileCategorical": ["#1d4ed8", "#0b0f19", "#60a5fa", "#1e3a8a", "#64748b",
						   "#0ea5e9", "#334155", "#93c5fd", "#2563eb", "#94a3b8"],
}

### Styling control via dictionary: modify it directly to control font sizes, line widths...
style_information = {
	"networkTitleFont":"1.5vh",
	"networkLabelFont":"1.5vh",
	"profileLabelFont":"1.5vh",
	"profileAxisTitleFont":"1.5vh",
	"profileAxisTickFont":"1.2vh",
	"profileLabelFont":"1.4vh",
	"profileLabelXOffset":-1,
	"profileLabelYOffset":2,
	"profileELabelYOffset":-20,
	"profileBoxHeight":2,
	"profileLineWidth":1
}

### CSS for the generated HTML. Bokeh 3 renders every model inside a shadow DOM, so styles are split:
### - amk_page_css_template: page shell (light DOM), injected through the HTML template.
### - amk_widget_css_template: attached to every Bokeh model as an InlineStyleSheet; rules on
###   :host(.class) style the model itself (css_classes), the rest style its internal elements.
amk_page_css_template = """
	body {
		background: $pageBackground;
		font-family: $fontBody;
		color: $textPrimary;
		margin: 0;
		border-top: 4px solid $accent;
	}
	.amk-shell {
		max-width: 1440px;
		margin: 0 auto;
		padding: 0 24px 40px;
	}
	.amk-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 12px;
		padding: 16px 0 14px;
		margin-bottom: 14px;
		border-bottom: 1px solid $border;
	}
	.amk-wordmark {
		font-family: $fontDisplay;
		font-weight: 800;
		font-size: 1.5rem;
		letter-spacing: -0.02em;
		color: $textPrimary;
	}
	.amk-wordmark span {
		color: $accent;
	}
	.amk-brand {
		display: flex;
		align-items: baseline;
		gap: 10px;
	}
	.amk-product {
		font-family: $fontDisplay;
		font-weight: 600;
		font-size: 1.15rem;
		color: $textSecondary;
		padding-left: 10px;
		border-left: 2px solid $accent;
	}
	.amk-logo {
		height: 56px;
		width: auto;
		display: block;
	}
	.amk-header-right {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 18px;
	}
	.amk-link {
		font-family: $fontBody;
		font-size: 0.88rem;
		font-weight: 600;
		color: $accent;
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 5px 12px 5px 8px;
		border: 1px solid $border;
		border-radius: 8px;
		transition: background-color .15s ease, border-color .15s ease;
	}
	.amk-link:hover {
		background-color: $accentSoft;
		border-color: $accent;
	}
	.amk-context {
		font-family: $fontBody;
		font-size: 0.95rem;
		font-weight: 600;
		color: $textPrimary;
		padding-left: 12px;
		border-left: 3px solid $accent;
	}
"""

amk_widget_css_template = """
	:host {
		font-family: $fontBody;
		color: $textPrimary;
	}
	.bk-btn.bk-btn-default {
		font-family: $fontBody;
		font-size: 0.85rem;
		font-weight: 600;
		padding: 7px 14px;
		background-color: $surface;
		color: $textPrimary;
		border: 1px solid $border;
		border-radius: 8px;
		cursor: pointer;
		transition: background-color .15s ease, color .15s ease, border-color .15s ease;
	}
	.bk-btn.bk-btn-default:hover:not(:disabled) {
		border-color: $accent;
		color: $accent;
		background-color: $accentSoft;
	}
	.bk-btn.bk-btn-default:disabled {
		color: $textMuted;
		cursor: default;
	}
	.bk-btn.bk-btn-default.bk-active {
		background-color: $accent;
		border-color: $accent;
		color: #ffffff;
	}
	.bk-input {
		font-family: $fontBody;
		font-size: 0.85rem;
		padding: 6px 10px;
		background-color: $surface;
		color: $textPrimary;
		border: 1px solid $border;
		border-radius: 8px;
	}
	.bk-input:focus {
		border-color: $accent;
		box-shadow: 0 0 0 3px $accentSoft;
		outline: none;
	}
	.bk-checkbox-group label, label {
		font-size: 0.85rem;
		color: $textPrimary;
	}
	input[type="checkbox"] {
		accent-color: $accent;
	}
	:host(.amk-menu) {
		align-items: center;
		flex-wrap: wrap;
		gap: 10px;
		padding: 10px 14px;
		margin-bottom: 18px;
		background: $surface;
		border: 1px solid $border;
		border-left: 4px solid $accent;
		border-radius: 10px;
	}
	:host(.amk-main) {
		gap: 18px;
		margin-bottom: 18px;
	}
	:host(.amk-card) {
		background: $surface;
		border: 1px solid $border;
		border-top: 3px solid $accent;
		border-radius: 10px;
		box-shadow: 0 1px 3px rgba(11, 15, 25, 0.06);
		padding: 14px 16px;
		overflow: hidden;
		gap: 8px;
	}
	:host(.amk-card-title) {
		font-family: $fontDisplay;
		font-weight: 700;
		font-size: 1rem;
		color: $textPrimary;
		padding-left: 10px;
		border-left: 4px solid $accent;
		line-height: 26px;
	}
	:host(.amk-mol-name) {
		margin-left: 16px;
		color: $accent;
		font-weight: 600;
		line-height: 26px;
	}
	:host(.amk-controls) {
		margin-left: auto;
		align-items: center;
		gap: 8px;
	}
	:host(.amk-field-label) {
		font-size: 0.85rem;
		color: $textSecondary;
	}
	:host(.amk-legend) {
		font-family: $fontBody;
		font-size: 0.82rem;
		color: $textSecondary;
	}
	:host(.amk-schemes) {
		overflow-y: auto;
		padding-left: 14px;
		border-left: 1px solid $border;
		font-size: 0.85rem;
	}
	.amk-schemes-title {
		font-weight: 700;
		color: $textPrimary;
		margin-bottom: 8px;
	}
	.amk-scheme-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.amk-scheme-list li {
		padding: 6px 0;
		border-bottom: 1px solid $border;
		line-height: 1.7;
	}
	.amk-scheme-num {
		display: inline-block;
		min-width: 20px;
		height: 20px;
		line-height: 20px;
		border-radius: 4px;
		color: #ffffff;
		text-align: center;
		font-weight: 700;
		font-size: 0.75rem;
		margin-right: 8px;
	}
	.amk-scheme-sp {
		font-weight: 600;
		color: $textPrimary;
	}
	.amk-scheme-ts {
		color: $accent;
		font-size: 0.8rem;
	}
	.amk-legend-swatch {
		display: inline-block;
		width: 16px;
		height: 3px;
		background: $highlight;
		margin-right: 6px;
		vertical-align: middle;
	}
"""

def amk_widget_stylesheet():
	'''Build the Bokeh InlineStyleSheet carrying the AutoMeKin widget styling (amk_widget_css_template)
	Output:
	- bkm.InlineStyleSheet object, to be appended to the stylesheets of every model in a layout'''
	return bkm.InlineStyleSheet(css=Template(amk_widget_css_template).substitute(amk_palette))

def apply_stylesheet(layout,stylesheet):
	'''Attach a stylesheet to every UI element (layouts, widgets, plots) referenced by a Bokeh layout,
	needed since Bokeh 3 isolates every model in its own shadow DOM
	Input:
	- layout. Bokeh layout (any UIElement).
	- stylesheet. bkm.InlineStyleSheet (or any Bokeh StyleSheet) to append.
	Output:
	- Modifies the stylesheets property of every UIElement in place'''
	for model in layout.references():
		if isinstance(model,bkm.UIElement) and stylesheet not in model.stylesheets:
			model.stylesheets = list(model.stylesheets) + [stylesheet]
	return None

# Basic management functions

def generate_inline_mol(xyzstring):
	'''Create a JSMol visualization from a newline-separated XYZ-format block
	Input:
	- xyzstring. String, XYZ formatted block of text, separated by newlines
	Output:
	- mol_script_string. String, containing a load data statement to load the molecule in JSMol'''
	xyzsubst = xyzstring.replace("\n","|")
	mol_script_string = r"data 'model X'|" + xyzsubst + r"|end 'model X';show data" 
	return mol_script_string 

def generate_inline_mol_freqs(data_dict):
	'''Create a JSMol visualization including vibrations: processes a whole ColumnDataSource object from
	bokeh to handle all required data: frequency values, mol. coordinates and displacements
	Input:
	- data_dict. Dictionary containing geometry, name, frequencies and vibr_displace fields (to make it compatible
	with both ColumnDataSource objects or with node/edge views)
	Output:
	- model_freq_block. String, containing a full LOAD DATA statement for JSMol, with separate models for each vibration'''
	# The try-except block allows to skip structures that lack required fields
	try:
		geo = data_dict["geometry"]
		name = data_dict["name"]
		frq = data_dict["frequencies"]
		displ = data_dict["vibr_displace"]
	except:
		return None
	# Handle cases where the edge has no info
	if (not (geo and frq and displ)):
		return None
	# we need to merge each displacement with the coordinates (and with a charge placeholder), and add the freq value as a comment
	freqvals = frq.split(";")
	coords = geo.split("\n")
	Nat = len(coords)
	displ_strings = [[" ".join(line) for line in dx] for dx in displ]
	model_freq_block = "load data 'model FRQS'\n"
	for jj,dx in enumerate(displ_strings):
		out_list = [line_crd + " 0 " + line_displ for line_crd,line_displ in zip(coords,dx)]	
		model_freq_block += "%d\n" % Nat
		model_freq_block += "frq = %.2f cm-1 \n" % float(freqvals[jj])
		model_freq_block += ("\n".join(out_list) + "\n")

	model_freq_block += "end 'model FRQS'"
	return model_freq_block	

def xyz_from_atoms(atomblock,comment=""):
	'''Generate a XYZ block from a block of text containing atoms and positions separated
	by newlines, as stored in the "geometry" property in RXReader
	Input:
	- atomblock. String, newline-separated geometry specification.
	- comment. String, text to be added in the comment line of the XYZ file
	Output:
	- block. String, newline-separated block in XYZ format (including no. of atoms and an optional comment)'''
	Nat = len(atomblock.split("\n"))
	block = "%d\n%s\n" % (Nat,comment)
	block += atomblock
	return block

def add_models(G):
	'''Add JSMol-compatible models from generate_inline_mol() for all nodes and edges in a graph
	Input:
	- G. nx.Graph object as generated from RXReader.
	Output:
	- Adds the "model" property to every node and edge
	'''
	for nd in G.nodes(data=True):
		geo = nd[1]["geometry"]
		xyz = xyz_from_atoms(geo,comment=nd[0])
		nd[1]["model"] = generate_inline_mol(xyz)

	for ed in G.edges(data=True):
		geo = ed[2]["geometry"]
		# Do not fail when there are empty blocks (e.g. for barrierless transition states)
		if (geo):
			xyz = xyz_from_atoms(geo,comment=ed[2]["name"])
			ed[2]["model"] = generate_inline_mol(xyz)
		else:
			ed[2]["model"] = None
	return None

def add_vibr_models(G):
	'''Add JSMol-compatible models from generate_inline_mol() for the vibrational displacements
	for all nodes and edges in a graph -> which must have been initialized through vibr_displ_parser()
	the property "vibr_displace" is available
	Input:
	- G. nx.Graph object as generated from RXReader -> with vibr_displ_parser().
	Output:
	- Adds the "vibr_models" property to every node and edge
	'''
	keys = ["geometry","name","frequencies","vibr_displace"]
	for nd in G.nodes(data=True):
		model_freq_block = generate_inline_mol_freqs(nd[1])
		nd[1]["vibr_models"] = model_freq_block

	for ed in G.edges(data=True):
		# Do not fail when there are empty blocks (e.g. for barrierless transition states)
		model_freq_block = generate_inline_mol_freqs(ed[2])
		ed[2]["vibr_models"] = model_freq_block

	return None

def generate_applet(width=600,height=600,alt_route=False,jsmol_resources={}):
	'''JSMol applet generation for a molecule with a given XYZ block, borrowed
	from example in original repo of jsmol_bokeh_extension. Relies on three main elements
	Input
	- width, height. Floats, size of the applet in pixels.
	- alt_route. If True, pass custom values for JSMol routes
	- jsmol_resources. Dictionary, mapping the serverURL, j2spath and js_url parameters to the desired JSMol locations
	Output:
	- info_dict. Dictionary with basic information to run JSMol.
	- applet. JSMol applet.
	- script_source. bokeh.ColumnDataSource object, allowing interactivity
	'''
	if (alt_route and len(jsmol_resources.keys()) == 3):
		serverURL = jsmol_resources["serverURL"]
		j2sPath = jsmol_resources["j2sPath"]
		js_url = jsmol_resources["js_url"]
	else:
		serverURL = "https://cdn.jsdelivr.net/gh/dgarayr/jsmol-test/jsmol/php/jsmol.php"
		j2sPath = "https://cdn.jsdelivr.net/gh/dgarayr/jsmol-test/jsmol/j2s"
		js_url = "https://cdn.jsdelivr.net/gh/dgarayr/jsmol-test/jsmol/JSmol.min.js"
	
	info_dict = dict(
		height="100%",
		width="100%",
		serverURL=serverURL,
		use="HTML5",
		j2sPath=j2sPath,
		script="background white;",
		disableJ2SLoadMonitor=True,
		disableInitialConsole=True
	)
	# Instantiate a new source: callbacks write a JSMol script to source.data["script"] and
	# emit source.properties.data.change, which is forwarded to the applet by js_run_script below
	script_source = bkm.ColumnDataSource({"script":[]})
	# Build applet. Bokeh 3 renders every model inside a shadow DOM, which breaks JSmol (it looks
	# up its own elements with document.getElementById), so JSmol runs in a same-origin iframe.
	# The iframe registers window.parent.amkJSmol.run(script) once the applet is ready, which
	# replaces the old jsmol_to_bokeh extension (Bokeh 2 only) without any compiled extension.
	applet_doc = Template("""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#ffffff;}</style>
<script src="$js_url"></script>
</head><body><div id="amk-jsmol" style="width:100%;height:100%;"></div>
<script>
var info = $info;
delete Jmol._tracker;
// avoid jsmol.php, which can be problematic (same patch used by jsmol_to_bokeh)
Jmol.$$ajax = function(ajaxInfo) {
	Jmol._ajaxCall = ajaxInfo.url;
	ajaxInfo.cache = (ajaxInfo.cache != "NO");
	ajaxInfo.url = Jmol._fixProtocol(ajaxInfo.url);
	var parsedUrl = new URL(ajaxInfo.url, document.baseURI);
	if (parsedUrl.searchParams.get("query") == null) {
		ajaxInfo.url = parsedUrl.href;
	} else {
		ajaxInfo.url = parsedUrl.searchParams.get("query");
	}
	return $$.ajax(ajaxInfo);
};
document.getElementById("amk-jsmol").innerHTML = Jmol.getAppletHtml("jmolApplet0", info);
jmolApplet0._cover(false);
var host = window.parent;
host.amkJSmol = {run: function(script) { Jmol.script(jmolApplet0, script); }};
if (host.amkJSmolPending) {
	host.amkJSmol.run(host.amkJSmolPending);
	host.amkJSmolPending = null;
}
</script></body></html>""").substitute(js_url=js_url,info=json.dumps(info_dict))
	iframe = '<iframe srcdoc="%s" style="width:%dpx;height:%dpx;border:0;display:block;" title="JSmol viewer"></iframe>' % (
		html.escape(applet_doc,quote=True),width,height)
	applet = bkm.Div(text=iframe,width=width,height=height,name="JSMOL")
	js_run_script = bkm.CustomJS(args={"source":script_source},code="""
		var script = source.data["script"][0]
		if (!script) { return }
		if (window.amkJSmol) {
			window.amkJSmol.run(script)
		} else {
			// applet still loading: keep the last script, the iframe runs it when ready
			window.amkJSmolPending = script
		}
	""")
	script_source.js_on_change("data",js_run_script)
	return info_dict,applet,script_source

def bokeh_network_view(G,positions=None,width=800,height=600,graph_title="Reaction network representation",out_backend="canvas",
					   map_field="energy",hide_energy=False,palette=amk_palette["nodeEnergyRamp"]):
	'''
	Generation of an interactive visualization of a RXReader-processed reaction network, via the
	from_networkx() method in Bokeh. 
	Input:
	- G. nx.Graph object as generated from RXReader.
	- positions. Dictionary, defining a layout for the graph nodes, as generated by any NetworkX layout generator.
	- width, height. Floats, dimensions of the figure
	- graph_title. String, label for the graph.
	- out_backend. Bokeh backend to be used for the Figure: use "canvas", as "svg" is possible but does not work well
	Output:
	- bfig. bokeh.plotting.figure() object, containing the graph, the corresponding node/edge labels & the basic interactive tools (pan, zoom,
	  reset, hovering...)
	- Gbok. Bokeh plot generated via from_networkx(),
	'''
	
	# Instantiate figure and graph, setting out basic parameters
	bfig = bokeh.plotting.figure(title=graph_title,width=width,height=height,tools="pan,wheel_zoom,box_zoom,reset,save",
				     x_range=bkm.Range1d(-1.2,1.2),y_range=bkm.Range1d(-1.2,1.2),
								 toolbar_location="above",output_backend=out_backend)
	bfig.axis.visible = False
	bfig.xgrid.grid_line_color = None
	bfig.ygrid.grid_line_color = None
	bfig.title.text_font_size = style_information["networkTitleFont"]
	bfig.title.text_font = amk_palette["fontDisplay"]
	bfig.title.text_color = amk_palette["textPrimary"]
	bfig.background_fill_color = amk_palette["surface"]
	bfig.border_fill_color = amk_palette["surface"]
	bfig.outline_line_color = amk_palette["border"]

	# Check if positions were passed, and create inside if necessary
	if (not positions):
		print("Generating network layout")
		positions = nx.kamada_kawai_layout(G)
	Gbok = bokeh.plotting.from_networkx(G,layout_function=positions,scale=1,center=(0,0))
	bfig.renderers.append(Gbok)

	# Modify how nodes are rendered: access the ColumnDataSource for energies and build the transformation
	nodesource = Gbok.node_renderer.data_source
	field_values = nodesource.data[map_field]
	colormap = bokeh.transform.linear_cmap(field_name=map_field,palette=palette,
									  low=min(field_values),high=max(field_values))
	Gbok.node_renderer.glyph = bkm.Scatter(marker="circle",size=30,fill_color=colormap,fill_alpha=0.5)
	Gbok.node_renderer.selection_glyph = bkm.Scatter(marker="circle",size=30,fill_color=colormap,fill_alpha=0.8,line_width=2)
	Gbok.node_renderer.hover_glyph = bkm.Scatter(marker="circle",size=30,fill_color=colormap,fill_alpha=0.7,line_color=colormap,
												line_width=2)

	# Legend for the node energy color mapping
	if (not hide_energy):
		color_bar = bkm.ColorBar(color_mapper=colormap['transform'],label_standoff=8,location=(0,0),
								 title="E (kcal/mol)",title_text_font=amk_palette["fontBody"],
								 title_text_font_size="1.3vh",title_text_color=amk_palette["textSecondary"],
								 major_label_text_font=amk_palette["fontBody"],major_label_text_font_size="1.1vh",
								 major_label_text_color=amk_palette["textSecondary"],
								 background_fill_color=amk_palette["surface"],border_line_color=None)
		bfig.add_layout(color_bar,'right')

	# For edges, only modify selection glyph by now
	edgesource = Gbok.edge_renderer.data_source
	Gbok.edge_renderer.glyph = bkm.MultiLine(line_width=1.5,line_color=amk_palette["textSecondary"],line_alpha=0.8)
	Gbok.edge_renderer.hover_glyph = bkm.MultiLine(line_width=2.5,line_color=amk_palette["accent"])
	Gbok.edge_renderer.selection_glyph = bkm.MultiLine(line_width=3,line_color=amk_palette["highlight"])

	# Add labels according to the positioning object, first for nodes and then for edges
	nodenames,coords = zip(*positions.items())
	# replace PROD by PR for nodenames
	xn,yn = zip(*coords)
	posnode_dict = {'xn':xn,'yn':yn,'nnames':nodenames}
	posnode = bkm.ColumnDataSource(posnode_dict)
	labels_node = bkm.LabelSet(x='xn', y='yn', text='nnames', text_font_style='bold',
				   x_offset=0, y_offset=5, source=posnode,
				   text_font_size=style_information["networkLabelFont"],
				   text_font=bokeh.core.properties.value(amk_palette["fontBody"]),text_color=amk_palette["textPrimary"])
	bfig.add_layout(labels_node)

	# TS labels: fetch central position and name for every edge (skipping barrierless ones)
	posedge_dict = {'xe':[],'ye':[],'enames':[],'etuples':[]}
	for ed in G.edges(data=True):
		if ("TSb" in ed[2]["name"]):
			continue
		xy1,xy2 = [positions[nn] for nn in ed[0:2]]
		mid = 0.5*(xy1+xy2)
		output = [mid[0],mid[1],ed[2]["name"],(ed[0],ed[1])]
		for ik,key in enumerate(['xe','ye','enames','etuples']):
			posedge_dict[key].append(output[ik])
	posedge = bkm.ColumnDataSource(posedge_dict)
	labels_edge = bkm.LabelSet(x='xe', y='ye', text='enames', text_font_style='bold',text_color=amk_palette["highlightInk"],
				   x_offset=0, y_offset=0, source=posedge,
							   text_font_size=style_information["networkLabelFont"],text_font=bokeh.core.properties.value(amk_palette["fontBody"]))
	bfig.add_layout(labels_edge)

	# Adding tools: hover & tap. To be able to see info about both nodes and edges, we must change the inspection policy
	# and add the two renderers (nodes & edges) explicitly to the constructor. 
	Gbok.inspection_policy = bkm.EdgesAndLinkedNodes()
	# Select the fields to be shown (with @) and optionally add formatting between curly braces

	# Custom JS selector for node hovering to have the formula field in the products
	hoverJS = '''
	var nrend = graph.node_renderer.data_source
	if (cb_data.index.indices.length > 0) {
		var ndx = cb_data.index.indices[0]
		var formula_list = nrend.data["formula"]
		// fallback for cases without any fragmentation, where formula is not defined
		if (formula_list){
			var formula = formula_list[ndx]
		} else {
			var formula = null
		}
		if (!formula){
			hover.tooltips = [["tag","@name"],["E","@energy{%.2f}"]]
 		} else {
			hover.tooltips = [["tag","@name"],["E","@energy{%.2f}"],["formula","@formula"]]
		}
	}
	'''
	### but this will be overridden if energy is hidden
	hover_node = bkm.HoverTool(description="Node hover",renderers=[Gbok.node_renderer],formatters={"@energy":"printf"})
	hover_node.callback = bkm.CustomJS(args=dict(hover=hover_node,graph=Gbok),code=hoverJS)
	hover_edge = bkm.HoverTool(description="Edge hover",tooltips=[("tag","@name"),("E","@energy{%.2f}")],
							   formatters={"@energy":"printf"},renderers=[Gbok.edge_renderer],line_policy="interp")
	if hide_energy:
		hover_node = bkm.HoverTool(description="Node hover",renderers=[Gbok.node_renderer],
								   tooltips=[("tag","@name")],formatters={"@energy":"printf"})
		hover_edge = bkm.HoverTool(description="Edge hover",tooltips=[("tag","@name")],
							   renderers=[Gbok.edge_renderer],line_policy="interp")
	bfig.add_tools(hover_node)
	bfig.add_tools(hover_edge)
	Gbok.selection_policy = bkm.EdgesAndLinkedNodes()
	tap = bkm.TapTool(renderers=[Gbok.node_renderer,Gbok.edge_renderer])
	bfig.add_tools(tap)
	# allow to hide tags, using a CustomAction
	# prepare simple 8x8 icon as a numpy array (8x8x3 for RGB)
	icon = np.zeros((8,8,3),dtype=np.uint8)
	# grey border and white inner region
	icon.fill(200)
	icon[1:-1,1:-1,:] = 255
	hide_count = 1		# inner state for the action
	hide_js = bkm.CustomJS(args={"figure":bfig,"counter":[hide_count]},code=js_callback_dict["hideLabels"])
	hide_action = bkm.CustomAction(icon=icon,callback=hide_js,description="Hide labels")
	bfig.add_tools(hide_action)

	# action to select neighbor nodes

	iconH = np.full(shape=(8,8,3),fill_value=255,dtype=np.uint8)
	iconH[1:-1,np.ix_([2,5]),:] = 200
	iconH[3:5,2:-2,:] = 200
	highl_callback = bkm.CustomJS(args={"graph":Gbok}, code=js_callback_dict["highlightNeighbors"])
	highlight = bkm.CustomAction(icon=iconH,callback=highl_callback,description="Highlight")
	bfig.add_tools(highlight)

	return bfig,Gbok

def profile_datasourcer(G,profile_list):
	'''Convert a list of profiles (obtained through arx.theor_profile_builder(), arx.theor_cycle_branch_builder(), or
	arx.poly_path_finder() and after application of arx.path_refformatter() to include transition states) to a list of 
	ColumnDataSource objects that can be used by Bokeh, with the structure
	ii | jj | energy | label, 
	where ii is the index of the profile and jj the order of the species
	Input:
	- G. nx.Graph object as generated from RXReader.
	- profile_list. List of lists of strings containing labels defining energy profiles, including TSs (via arx.path_reformatter()).
	Output:
	- cds_list. List of ColumnDataSource objects defining all required energy profiles'''
	cds_list = []
	for ii,prof in enumerate(profile_list):
		# fix TS names, taking the corresponding nodes as reference
		tuple_prof = [(prof[jj-1],prof[jj+1]) if "TS" in entry else entry for jj,entry in enumerate(prof)]
		# Filter out barrierless TS: find indices & then select on tuple-based profile 
		kept_ndx = [ii for ii,entry in enumerate(prof) if "TSb" not in entry]
		cleaned_prof = [prof[ii] for ii in kept_ndx]
		working_prof = [tuple_prof[ii] for ii in kept_ndx]
		# Prepare the lines, as in arx.theor_profile_plotter(), duplicating entries
		xvals = np.arange(0,2*len(working_prof),dtype="float64")
		energies = [arx.simple_prop_fetch(G,entry,"energy") for entry in working_prof]
		# formulas shall only be fetched for PRODUCTS
		formulas = [arx.simple_prop_fetch(G,entry,"formula") if "PR" in entry else None for entry in working_prof]
		yvals = [e for evalue in energies for e in (evalue,evalue)]
		labels = [lab for labvalue in cleaned_prof for lab in (labvalue,labvalue)]
		formula_col = [form for formula in formulas for form in (formula,formula)]
		# save as ColumnDataSource
		prof_cds = bkm.ColumnDataSource(data={"x":xvals,"y":yvals,"lab":labels,"form":formula_col})
		cds_list.append(prof_cds)
	return cds_list

def reaction_schemes_html(G,profile_list):
	'''Build an HTML list with the reaction scheme (MIN -TS-> MIN ...) of every energy profile, numbered
	and colored as the corresponding line in profile_bokeh_plot()
	Input:
	- G. nx.Graph object as generated from RXReader.
	- profile_list. List of lists of strings containing labels defining energy profiles, including TSs (via arx.path_reformatter()).
	Output:
	- html_text. String, HTML block to be placed in a bkm.Div'''
	palette = amk_palette["profileCategorical"]
	items = []
	for ii,prof in enumerate(profile_list):
		color = palette[ii % 10]
		parts = []
		for entry in prof:
			if ("TS" in entry):
				parts.append("<span class='amk-scheme-ts'>&mdash;%s&rarr;</span>" % html.escape(entry))
			else:
				parts.append("<span class='amk-scheme-sp'>%s</span>" % html.escape(entry))
		items.append("<li><span class='amk-scheme-num' style='background:%s'>%d</span>%s</li>" % (color,ii+1," ".join(parts)))
	html_text = "<div class='amk-schemes-title'>Reaction schemes</div><ol class='amk-scheme-list'>%s</ol>" % "".join(items)
	return html_text

def profile_bokeh_plot(G,profile_list,condition=[],width=600,height=600,out_backend="canvas"):
	'''Generate a Bokeh figure for energy profiles, using profile_datasourcer() to transform the profile list to a 
	ColumnDataSource list.
	Input:
	- G. nx.Graph object as generated from RXReader.
	- profile_list. List of lists of strings containing labels defining energy profiles, including TSs (via arx.path_reformatter()).
	- condition. List of booleans, if same length as profile_list, profiles where the list is False will not be shown.
	Output:
	- bfig. Bokeh figure containing line plots & labels for every profile in profile_list
	'''
	# Initialization: instantiate figure, remove X-axis and add palette
	bfig = bokeh.plotting.figure(width=width,height=height,tools="pan,wheel_zoom,box_zoom,reset,save",name="PROFILE",
								 min_border_left=int(width/10),output_backend=out_backend)
	bfig.xaxis.visible = False
	bfig.yaxis.axis_label = "E (kcal/mol)"
	bfig.yaxis.axis_label_text_font = amk_palette["fontBody"]
	bfig.yaxis.axis_label_text_font_size = style_information["profileAxisTitleFont"]
	bfig.yaxis.axis_label_text_font_style = "bold"
	bfig.yaxis.axis_label_text_color = amk_palette["textPrimary"]
	bfig.yaxis.major_label_text_font = amk_palette["fontBody"]
	bfig.yaxis.major_label_text_font_size = style_information["profileAxisTickFont"]
	bfig.yaxis.major_label_text_color = amk_palette["textSecondary"]
	bfig.background_fill_color = amk_palette["surface"]
	bfig.border_fill_color = amk_palette["surface"]
	bfig.outline_line_color = amk_palette["border"]
	palette = amk_palette["profileCategorical"]

	# Generate the list of ColumnDataSources
	cds_paths = profile_datasourcer(G,profile_list)
	# Check condition
	if (len(condition) != len(profile_list)):
		condition = [True for prof in profile_list]

	skeleton_lines = []
	# Iterate & plot
	for ii,cdspath in enumerate(cds_paths):
		Nentries = len(cdspath.data["lab"])
		cndx = (ii % 10)
		rx_line = bfig.line(x="x",y="y",color=palette[cndx],source=cdspath,line_width=style_information["profileLineWidth"])
		skeleton_lines.append(rx_line)
		# Prepare labels, slicing the original CDS to avoid repetitions
		cds_lab = bkm.ColumnDataSource({k:cdspath.data[k][::2] for k in ["x","y","lab"]})
		cds_lab.data["elab"] = np.array(["%.1f" % float(e) for e in cds_lab.data["y"]])
		cds_lab.data["x"] = np.array([(float(item) + 0.5) for item in cds_lab.data["x"]])
		rect = bkm.Rect(x="x",y="y",fill_color=palette[cndx],fill_alpha=0.9,width=1,height=style_information["profileBoxHeight"],line_width=0,name="RECTANGLE")
		rx_rect = bfig.add_glyph(cds_lab,rect)

		# Do a copy for the labels to avoid problems with mutability
		cds_lab_textlab = bkm.ColumnDataSource(copy.deepcopy(cds_lab.data))
		rx_label = bkm.LabelSet(x="x",y="y",text="lab",source=cds_lab_textlab,x_offset=style_information["profileLabelXOffset"],y_offset=style_information["profileLabelYOffset"],
								name="THELABELS",text_font_size=style_information["profileLabelFont"],
								text_font=bokeh.core.properties.value(amk_palette["fontBody"]),text_color=amk_palette["textPrimary"],text_font_style="bold")
		bfig.add_layout(rx_label)
		cds_lab_elab = bkm.ColumnDataSource(copy.deepcopy(cds_lab.data))
		energy_label = bkm.LabelSet(x="x",y="y",text="elab",source=cds_lab_elab,x_offset=style_information["profileLabelXOffset"],
									y_offset=style_information["profileELabelYOffset"],name="ENERGYLABELS",
									text_font_size=style_information["profileLabelFont"],
									text_font=bokeh.core.properties.value(amk_palette["fontBody"]),text_color=amk_palette["textPrimary"])
		bfig.add_layout(energy_label)
		### Add filtering: hide when filter condition is not fulfilled
		rx_line.visible = condition[ii]
		rx_rect.visible = condition[ii]
		rx_label.visible = condition[ii]
		energy_label.visible = False

	# And add the hover, with custom callback to hide the "formula" field outside products
	hover_prof = bkm.HoverTool(description="Profile hover",tooltips=[("tag","@lab"),("E","@y{%.2f}"),("formula","@form")],
							   formatters={"@y":"printf"},renderers=skeleton_lines,line_policy="interp")
	hover_profJS = '''
	// all renderers are checked at once: when the triggered one is caught (by changes in cb_data.index.line_indices)
	// access its data_source directly
	if (cb_data.index.line_indices.length > 0) {
		var ndx = cb_data.index.line_indices[0]
		var rend_obj = cb_data.renderer.data_source
		var formula_list = rend_obj.data["form"]

	// fallback for cases without any fragmentation, where formula is not defined
	    if (formula_list){
			var formula = formula_list[ndx]
		} else {
			var formula = null
		}
	    if (!formula){
			hover.tooltips = [["tag","@lab"],["E","@y{%.2f}"]]
 		} else {
			hover.tooltips = [["tag","@lab"],["E","@y{%.2f}"],["formula","@form"]]
		}
	}
	'''

	hover_prof.callback = bkm.CustomJS(args=dict(hover=hover_prof),code=hover_profJS)
	
	bfig.add_tools(hover_prof)
	bfig.js_on_event('reset',bkm.CustomJS(args = {"prof":bfig}, code = js_callback_dict["resetProfile"]))
	return bfig
		
js_callback_dict = {
	# Dictionary storing JS code for bokeh.models.CustomJS definitions
	"loadMolecule":"""
		// from graph, we fetch nrend - node renderer, erend - edgerenderer
		//source - source object for JSMol
		var nrend = graph.node_renderer.data_source
		var erend = graph.edge_renderer.data_source
		if (cb_obj.indices.length) {
			var ninds = nrend.selected.indices
			var einds = erend.selected.indices
			if (ninds.length) {
				var rend = nrend
			} else {
				var rend = erend
			}
			var ndx = rend.selected.indices[0]
			var model = rend.data["model"][ndx]
			if (model == null){
				// clear view if no model is available
				model = "backbone only ; backbone off"
			}
			var molname = rend.data["name"][ndx]
			textField.text = "<font size=+1><b>" + molname + "</b></font>"
			source.data["script"] = [model]
			source.properties.data.change.emit()
		}
		""",

	"loadVibrations":"""
		// from graph, we fetch nrend - node renderer, erend - edgerenderer, 
		// source - source object for JSMol, menu - dropdown menu to change vibrations
		var nrend = graph.node_renderer.data_source
		var erend = graph.edge_renderer.data_source
		
		var ninds = nrend.selected.indices
		var einds = erend.selected.indices
		if (ninds.length) {
			var rend = nrend
		} else {
			var rend = erend
		}
		var ndx = rend.selected.indices[0]
		var vibr_models = rend.data["vibr_models"][ndx]
		if (vibr_models.length){
			source.data["current_model"] = [vibr_models]
			source.data["script"] = [vibr_models + "; vibration on ; vibration scale 0.25"]
			source.data["current_mol"] = rend.data["name"][ndx]
			// and also populate the normal mode dropdown: get the frequencies and assign them to menu
			// we must pass indices as strings for it to work, add 1 to match model numbering
			menu.disabled = false
			var freqlist = rend.data["frequencies"][ndx].split(";")
			var menulist = freqlist.map(function (frq,ii) {return [frq+" cm-1",(ii+1).toString()]})
			menu.menu = menulist
			var nw_label = "Normal modes (" + source.data["current_mol"] + ")"
			menu.label = nw_label
			// modify text element using the BASE frequency
			var molname = source.data["current_mol"]
			var frqval = freqlist[0].toString().trim() + " cm-1"
			textField.text = "<font size=+1><b>" + molname + " (" + frqval + ")" + "</b></font>"
		}
	
		source.properties.data.change.emit()
		""",

	"molToClipboard":"""
		// from graph, we fetch nrend - node renderer, erend - edgerenderer
		// source - source object for JSMol, button - button object
		var nrend = graph.node_renderer.data_source
		var erend = graph.edge_renderer.data_source

		var ninds = nrend.selected.indices
		var einds = erend.selected.indices
		if (ninds.length) {
			var rend = nrend
			} else {
			var rend = erend
		}
		var ndx = rend.selected.indices[0]
		var geo = rend.data["geometry"][ndx]
		var name = rend.data["name"][ndx]
		var orig_label = button.label
		// use a function to apply setTimeout and recover original label
		function recover_label(button,orig_label){
			button.label = orig_label
		}	

		if (geo.length){
			navigator.clipboard.writeText([geo])
			button.label = "Copied " + name + "!"
			setTimeout(recover_label,2000,button,orig_label)
		}
		""",

		"locateMolecule":"""
		// source - source object for JSMol
		// pass graph and fetch node and edge renderers
		// from fig, we modify x_range and y_range. Default plot starts from -1.2 to 1.2,
		var nrend = graph.node_renderer.data_source
		var erend = graph.edge_renderer.data_source
		var layout = graph.layout_provider.graph_layout
		// fetch the query in the data sources, choosing the appropiate renderer depending on the query
		var mol_query = text_input.value
		if (mol_query.includes("TS") || mol_query.includes("ts")) {
			var renderer = erend
			var other_renderer = nrend
		} else {
			var renderer = nrend
			var other_renderer = erend
		}
		var pool_names = renderer.data["name"]
		// split species joined by + sign
		var pool_species = pool_names.reduce((acc,name) =>
					{acc.push(name.split("+"));
					return acc},[])
		// function to match results in the array
		var getSubstringIndices = function(arr,query){
			return arr.reduce(
					function(matches,tgt,i){
							if (tgt.includes(query))
						{matches.push(i)};
							return matches;
					},
					[]);
		}

		if (!mol_query.includes("+")) {
			var ndx = getSubstringIndices(pool_species,mol_query)
		} else {
			var ndx_u = pool_names.indexOf(mol_query)
			if (ndx_u < 0) {
				var ndx = []
			} else {
				var ndx = [ndx_u]
			}
		}
		// locate positions of the node or of the nodes defining an edge
		if (mol_query.includes("TS") || mol_query.includes("ts")) {
			var n1 = renderer.data["start"][ndx]
			var n2 = renderer.data["end"][ndx]
			var pos1 = layout[n1]
			var pos2 = layout[n2]
			var positions = new Array(2)
			positions[0] = 0.5*(pos1[0]+pos2[0])
			positions[1] = 0.5*(pos1[1]+pos2[1])
		} else {
			var positions = layout[pool_names[ndx[0]]]
		}
		if (ndx.length > 0) {
			// clearing other sel. avoids problems for model loading sometimes
			other_renderer.selected.indices = []
			renderer.selected.indices = ndx
			fig.x_range.start = positions[0] - 0.5
			fig.x_range.end = positions[0] + 0.5
			fig.y_range.start = positions[1] - 0.5
			fig.y_range.end = positions[1] + 0.5
		}
		""",

		"chooseVibrationMenu":"""
		// source - source object for JSMol ; menu - dropdown menu object
		source.data["script"] = [source.data["current_model"] + "; vibration on ; vibration scale 0.25 ; model " + cb_obj.item]
		var ndx = parseInt(cb_obj.item) - 1
		var molname = source.data["current_mol"]
		var frqval = menu.menu[ndx][0]
		source.data["current_vibration"] = frqval
		textField.text = "<font size=+1><b>" + molname + " (" + frqval.trim() + ")" + "</b></font>"
		source.properties.data.change.emit()
		""",

		"selectProfileByMol":"""
		// graph - bokeh graph for the network view, use to fetch node and edge renderers
		// prof - bokeh figure for the profiles
		var nrend = graph.node_renderer.data_source
		var erend = graph.edge_renderer.data_source
		var ninds = nrend.selected.indices
		var einds = erend.selected.indices
		if (ninds.length) {
			var rend = nrend
		} else if (einds.length) {
			var rend = erend
		} else {
			var rend = null
			// make everything visible
			for (let [index,line] of prof.renderers.entries()){
				prof.renderers[index].visible = true
				// only EVEN entries for center
				if (index % 2 == 0){
					prof.center[index+2].visible = true
				}
			} 
			return true
		}
		var ndx = rend.selected.indices[0]
		var sel_spc = rend.data["name"][ndx]
		// labels are stored in "center" property of the figure
		// and we have TWO renderers per entry: skeleton and rectangle
		var Nlines = prof.renderers.length/2
		for (let i = 0 ; i < Nlines ; i++){
			const index = 2*i
			var current_data = prof.renderers[index].data_source
			var labels = current_data.data["lab"]
			// use ! to negate inclusion
			if (!labels.includes(sel_spc)){
				prof.renderers[index].visible = false
				prof.renderers[index+1].visible = false
				// labels are also duplicated: first tag, then energy.
				prof.center[index+2].visible = false
				prof.center[index+3].visible = false
			} 
		prof.properties.renderers.change.emit()
		}
		""",

		"selectProfileByEnergy":"""
		// graph - bokeh graph for the network view, use to fetch node and edge renderers
		// prof - bokeh figure for the profiles, thrbox - textbox for threshold energy
		var thr = parseFloat(thrbox.value)
		var range = {min: thr, max: thr}
		function overThreshold(element){
			return element > thr
		}
		var Nlines = prof.renderers.length/2
		for (let i = 0 ; i < Nlines ; i++){
			const index = 2*i
			var current_data = prof.renderers[index].data_source
			var energies = current_data.data["y"]
			//hide if anything is above the threshold
			if (energies.some(overThreshold)){
				prof.renderers[index].visible = false
				prof.renderers[index+1].visible = false
				// labels are also duplicated: first tag, then energy.
				prof.center[index+2].visible = false
				prof.center[index+3].visible = false
			} 
		}
		""",

		"resetProfile":"""
		// prof - bokeh figure for the profiles
		// make everything visible
		var Nlines = prof.renderers.length/2
		for (let i = 0 ; i < Nlines ; i++){
			const index = 2*i
			prof.renderers[index].visible = true
			prof.renderers[index+1].visible = true
			// tags are EVEN entries and energies are ODD
			prof.center[index+2].visible = true
			prof.center[index+3].visible = false
		}
		""",

		"hideLabels":"""
		// hide all labels from a reaction network
		// figure - bokeh FIGURE for the network view, counter - inner counter for state, use list for mutability
		// edit the 3rd and 4th elements of the figure.center array, containing labelsets
		// 0 - all labels on, 1 - TS labels off, 2 - all labels off
		var ct = counter[0]
		switch (ct) {
			case 0:
				figure.center[2].visible = true
				figure.center[3].visible = true
				break
			case 1:
				figure.center[2].visible = true
				figure.center[3].visible = false
				break
			case 2:
				figure.center[2].visible = false
				figure.center[3].visible = false
				break
		}
		ct = ct + 1
		if (ct >= 3) {
			ct = 0
		}
		counter[0] = ct
		""",

	"showEnergyLabels":"""
	// show ENERGY labels for the profile
	// prof - bokeh profile for figures, state - counter for the inner state
	state[0] = !state[0]
	var Nlines = prof.renderers.length/2
	for (let i = 0 ; i < Nlines ; i++){
		// show or hide for ODD ii values (energy label) AND only for visible renderers
		var jj = 2*i + 1
		if (prof.renderers[jj-1].visible == true){
			prof.center[jj+2].visible = state[0]
		} 
	}
	""",
	"highlightNeighbors":'''
	var nrend = graph.node_renderer.data_source
	var erend = graph.edge_renderer.data_source
	var nodenames = nrend.data["name"]
	var neighborhood = []
	var ndx = Array.from(nrend.selected.indices)
	for (let j = 0; j < ndx.length ; j++){
		var j_ndx = ndx[j]
		var current_neighborhood = nrend.data["neighbors"][j_ndx]
		var nw_neighborhood = neighborhood.concat(current_neighborhood)
		neighborhood = nw_neighborhood
	}
	var neighIdx = Array.from(ndx)
	for (let i = 0 ; i < neighborhood.length ; i++) {
		var i_idx = nodenames.indexOf(neighborhood[i])
		neighIdx.push(i_idx)
		}
	// keep the first one as first selected
	nrend.selected.indices = neighIdx
	// select all edges where the initial node participates
	var all_edge_indices = []
	for (let j = 0; j < ndx.length ; j++){
		var j_ndx = ndx[j]
		var nd_sel = nodenames[j_ndx]
		var start_from_ndx = erend.data["start"].map((nd,i) => nd === nd_sel ? i : -1).filter(index => index !== -1)
		var end_from_ndx = erend.data["end"].map((nd,i) => nd === nd_sel ? i : -1).filter(index => index !== -1)
		var nw_edge_indices = start_from_ndx.concat(end_from_ndx)
		all_edge_indices = all_edge_indices.concat(nw_edge_indices)
	}
	erend.selected.indices = []
	erend.selected.indices = all_edge_indices

	''',
	"showSelectedOnly":'''
		var nrend = graph.node_renderer.data_source
		var erend = graph.edge_renderer.data_source
		var nodesel = nrend.selected.indices
		var edgesel = erend.selected.indices
		var nodeindices = nrend.data["index"]
		var edgenames = erend.data["name"]

		var numNodes = nodeindices.length
		var numEdges = edgenames.length

		// access the labels too
		var labsNodes = figure.center[2].source.data
		var labsEdges = figure.center[3].source.data
		if (box.active.length >= 1){
			var k = 0
			for (let i = 0; i < numNodes ; i++) {
				if (!nodesel.includes(i)){
						nrend.data["index"][i] = null
						labsNodes["nnames"][i] = " "
				}
			}
			for (let j = 0; j < numEdges ; j++) {
				var is_tsb = edgenames[j].includes("TSb")
				if (!edgesel.includes(j)){
					erend.data["start"][j] = null
					erend.data["end"][j] = null
					if (!is_tsb){
						labsEdges["enames"][k] = " "
					}
				}
				if (!is_tsb){k += 1}
			}
		} else {
			var k = 0
			for (let i = 0; i < numNodes ; i++) {
				nrend.data["index"][i] = backupNodeIdxs[i]
				labsNodes["nnames"][i] = labsNodes["labCopy"][i]
			}
			for (let j = 0; j < numEdges ; j++) {
				var is_tsb = edgenames[j].includes("TSb")
				erend.data["start"][j] = backupEdgeRoutes["start"][j]
				erend.data["end"][j] = backupEdgeRoutes["end"][j]
				if (!is_tsb) {
					labsEdges["enames"][k] = labsEdges["labCopy"][k]
				}
				if (!is_tsb){k += 1}
			}
		}

		nrend.change.emit()
		erend.change.emit()
	'''

}

def full_view_layout(bokeh_figure,bokeh_graph,G=None,alt_jsmol=False,jsmol_resources={},sizing_dict={}):
	'''
	Combination of the interactive graph visualization generated by bokeh_network_view with a JSMol instance and the
	corresponding interaction buttons. Molecules are shown by clicking in each edge or node.
	All callbacks use JavaScript code, not Python, so no live Bokeh server is required at all.
	Input:
	- bokeh_figure, bokeh_graph. Output of bokeh_network_view()
	- G. NetworkX.Graph(). Used for profile support: profiles are only added if G is not None and if it contains a pathList
	property.
	- alt_jsmol. Boolean, if True, use an alternative instance of JSMol, with the links in jsmol_resources
	- jsmol_resources. Dictionary, mapping the serverURL, j2spath and js_url parameters to the desired
	JSMol locations
	'''
	# Control the sizes
	if (sizing_dict):
		w1 = sizing_dict['w1']		# network plot width
		w2 = sizing_dict['w2']		# JSMol & profile plot width
		h = sizing_dict['h']		# height for main plots
	else:
		w1,w2,h = (800,600,800)
	hw = int(h/6)
	# Add access to data sources for nodes and edges
	nodesource = bokeh_graph.node_renderer.data_source
	edgesource = bokeh_graph.edge_renderer.data_source
	# Instantiate the applet: the viewer card stacks a title row (26 px) and the applet, while the
	# network card stacks its title (26), the figure (h) and the legend (24), plus gaps: match both cards
	h_view = h + 32
	# energy profiles go below both cards, using the full width (two cards + card padding/margins)
	w_prof = w1 + w2 + 72
	h_prof = int(h*0.75)
	info,app,script_source = generate_applet(width=w2,height=h_view,alt_route=alt_jsmol,jsmol_resources=jsmol_resources)

	# Instantiate the required widgets: buttons, text inputs, menus...
	
	b1 = bkm.Button(label="Load vibrations",align="center") 
	b2 = bkm.Button(label="Copy XYZ",align="center")
	text_input = bkm.TextInput(value=nodesource.data["name"][0],width=160,align="center",placeholder="MIN1, TS3, PR2...")
	b3 = bkm.Button(label="Locate",align="center")
	cb_isol = bkm.CheckboxGroup(labels=["Isolate selection"],align="center")
	menu = bkm.Dropdown(label="Normal modes",menu=[("No vibr. loaded","None"),None],disabled=True,align="center")
	text = bkm.Div(text="(Click an element)",align="center")
	# For profile-based elements
	b4 = bkm.Button(label="Filter by selected species",align="center",disabled=True)
	b5 = bkm.Button(label="Filter by energy",align="center",disabled=True)
	thrbox = bkm.TextInput(value="%.2f" % max(edgesource.data["energy"]),width=110,align="center")
	# Write the JavaScript callback to allow to avoid the Bokeh server: all is ported to JavaScript
	# For this to work, we need to pre-load all models in the graph
	js_load_mol = bkm.CustomJS(args = {"graph":bokeh_graph,"source":script_source,"textField":text}, 
							   code = js_callback_dict["loadMolecule"])

	js_load_vibrations = bkm.CustomJS(args = {"graph":bokeh_graph,"source":script_source,"menu":menu,"textField":text}, 
									  code = js_callback_dict["loadVibrations"])

	js_geo_clipboard = bkm.CustomJS(args = {"graph":bokeh_graph,"source":script_source,'button':b2}, 
									code = js_callback_dict["molToClipboard"])

	js_mol_locator = bkm.CustomJS(args = {"graph":bokeh_graph,"fig":bokeh_figure,"text_input":text_input},
								  code = js_callback_dict["locateMolecule"])
	
	js_menu_selector = bkm.CustomJS(args = {"source":script_source,"menu":menu,"textField":text},
					 			    code = js_callback_dict["chooseVibrationMenu"])

	### prepare backup data for hiding
	backup_node_indices = copy.deepcopy(nodesource.data["index"])
	backup_edges = {"start":copy.deepcopy(edgesource.data["start"]),
					"end":copy.deepcopy(edgesource.data["end"])}

	bokeh_figure.center[2].source.data["labCopy"] = bokeh_figure.center[2].source.data["nnames"]
	bokeh_figure.center[3].source.data["labCopy"] = bokeh_figure.center[3].source.data["enames"]


	js_isolate_selected = bkm.CustomJS(args={'backupNodeIdxs':backup_node_indices,'backupEdgeRoutes':backup_edges,'graph':bokeh_graph,
											 'colNames':nodesource.column_names,'box':cb_isol,'figure':bokeh_figure},
										code=js_callback_dict["showSelectedOnly"])


	# Set up the JS callbacks for nodes and edges
	bokeh_graph.node_renderer.data_source.selected.js_on_change('indices',js_load_mol)
	bokeh_graph.edge_renderer.data_source.selected.js_on_change('indices',js_load_mol)
	# Widget callbacks
	# Button 1: load vibrational models
	b1.js_on_click(js_load_vibrations)
	# Button 2: pass current geometry to clipboard
	b2.js_on_click(js_geo_clipboard)
	# Allow to select by name
	b3.js_on_click(js_mol_locator)
	# Isolate selection
	cb_isol.js_on_change("active",js_isolate_selected)
	# Vibration selector
	menu.js_on_event("menu_item_click",js_menu_selector)
	
	# Layout (AutoMeKin-X dashboard):
	# | MENU: Load vibr. | Modes | Clipboard | [text] Locate | Isolate selection          |
	# | Molecule viewer (JSMol)          || Reaction network                               |
	# | Energy profiles + filters (full width, only when paths were requested)            |

	menu_bar = bkm.Row(b1,menu,b2,text_input,b3,cb_isol,css_classes=['amk-menu'],sizing_mode="stretch_width")

	# Viewer card (left): title + currently loaded molecule, then the JSMol applet
	viewer_title = bkm.Div(text="Molecule viewer",css_classes=['amk-card-title'],height=26)
	text.css_classes = ['amk-mol-name']
	text.height = 26
	col_viewer = bkm.Column(bkm.Row(viewer_title,text),app,css_classes=['amk-card','amk-card-viewer'])

	# Network card (right). A real Bokeh Div is used for the title (Bokeh figures render into a canvas)
	network_title = bkm.Div(text="Reaction network",css_classes=['amk-card-title'],height=26)
	legend = bkm.Div(text="<span class='amk-legend-swatch'></span> selected / highlighted route",
					 css_classes=['amk-legend'],height=24)
	col_network = bkm.Column(network_title,bokeh_figure,legend,css_classes=['amk-card','amk-card-network'])

	layout = bkm.Row(col_viewer,col_network,css_classes=['amk-main'])
	rows = [menu_bar,layout]

	# Energy profiles (bottom) if G was passed to the function and contains a pathList property
	if (G and "pathList" in G.graph):
		b4.disabled = False
		b5.disabled = False
		# the profile plot shares the bottom card with the reaction schemes list (w_scheme px)
		w_scheme = 320
		fig_prof = profile_bokeh_plot(G,G.graph["pathList"],width=w_prof-w_scheme-20,height=h_prof)
		js_select_profile_mol = bkm.CustomJS(args = {"graph":bokeh_graph,"prof":fig_prof}, 
											 code = js_callback_dict["selectProfileByMol"])
		b4.js_on_click(js_select_profile_mol)
		js_select_profile_e = bkm.CustomJS(args = {"prof":fig_prof,"thrbox":thrbox}, 
										   code = js_callback_dict["selectProfileByEnergy"])
		b5.js_on_click(js_select_profile_e)

		elabel_state = False
		# Add a CustomAction here for energy label management
		js_show_elabels = bkm.CustomJS(args={"prof":fig_prof,"state":[elabel_state]},
										code = js_callback_dict["showEnergyLabels"])
		# custom icon
		iconE = np.full(shape=(8,8,3),fill_value=255,dtype=np.uint8)
		iconE[np.ix_([1,4,7]),1:-1,:] = 200
		iconE[1:-1,1,:] = 200
		elabel_action = bkm.CustomAction(icon=iconE,callback=js_show_elabels,description="Show energy labels")
		fig_prof.add_tools(elabel_action)

		profile_title = bkm.Div(text="Energy profiles",css_classes=['amk-card-title'],height=26)
		thr_label = bkm.Div(text="Max. energy (kcal/mol)",css_classes=['amk-field-label'],align="center")
		b6 = bkm.Button(label="Show all",align="center")
		b6.js_on_click(bkm.CustomJS(args={"prof":fig_prof},code=js_callback_dict["resetProfile"]))
		control_row = bkm.Row(b4,thr_label,thrbox,b5,b6,css_classes=['amk-controls'])
		schemes = bkm.Div(text=reaction_schemes_html(G,G.graph["pathList"]),width=w_scheme,height=h_prof,
						  css_classes=['amk-schemes'])
		col_profile = bkm.Column(bkm.Row(profile_title,control_row),bkm.Row(fig_prof,schemes),
								 css_classes=['amk-card','amk-card-profile'])
		rows.append(col_profile)

	full_layout = bkm.Column(*rows,css_classes=['amk-page'])
	apply_stylesheet(full_layout,amk_widget_stylesheet())
	return full_layout


def generate_visualization(G,finaldir,title,outfile,Nvibrations=-1,with_profiles=False,size=(1400,800),
						   layout_function=nx.kamada_kawai_layout,geo_molden_update=True,
						   jsmol_resources={},local_resources=False,generate_file=True):
	'''Wrapper function to generate HTML visualizations for a given network
	Input:
	- G. nx.Graph object as generated from RXReader. For profile support, it should contain a graph["pathList"] property.
	- finaldir. String, name of the folder to fetch calculations from (FINAL_LL/FINAL_HL)
	- title. String, title for the visualization.
	- outfile. String, name of the output HTML file.
	- Nvibrations. Integer, no. of vibrations to be loaded in the visualization. 0: skip vibration loading, -1, load all
	- with_profiles. Boolean, if True, add profile visualization.
	- size. Tuple of integers,size of the final visualization in pixels.
	- layout_function. Function to generate graph layout.
	- geo_molden_update. Boolean, if True, update geometries with the MOLDEN files in normal_modes/
	- jsmol_resources. Dictionary, mapping the serverURL, j2spath and js_url parameters to the desired JSMol locations. If empty, use default server.
	- local_resources. Boolean, if True, include inline BOkeh libraries in the HTML.
	- generate_file. Boolean, if True build the HTML visualization, else just create the layout object
	Output:
	- lay. Bokeh layout as generated by full_view_layout()
	'''
	
	### Define sizing
	# The amk-card wrapper (see style_template below) adds real padding/chrome
	# around each Bokeh layout column (18px+20px horizontal, title + padding
	# vertical); Bokeh's own layout engine positions children with absolute
	# pixel boxes that know nothing about that CSS padding, so the inner
	# figure/applet size is shrunk here to actually fit inside the card
	# instead of overflowing past its rounded corners.
	CARD_INSET_W = 48
	CARD_INSET_H = 60
	w1 = int(size[0]*4/7) - CARD_INSET_W
	w2 = int(size[0]*3/7) - CARD_INSET_W
	wu = int(size[0]/7)
	h = int(size[1]*6/8) - CARD_INSET_H

	sizing_dict = {'w1':w1,'w2':w2,'wu':wu,'h':h}

	### Page-level styling (AutoMeKin visual identity, see amk_palette at the top of this module).
	### Only the page shell (header, background) lives in the light DOM and is styled here: since
	### Bokeh 3, every widget/plot renders inside its own shadow DOM, so their styles are attached
	### to each model through amk_widget_stylesheet() instead (see full_view_layout()).
	### string.Template ($name substitution) is used instead of str.format()/f-strings so that CSS's
	### own curly braces -- and the Jinja2 {% block %} / {{ }} syntax used by Bokeh's HTML
	### template -- never collide with Python's string formatting syntax.
	amk_style_css = Template(amk_page_css_template).substitute(amk_palette)

	style_template = """
	{% block postamble %}

	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
	<style>
	""" + amk_style_css + """
	</style>
	{% endblock %}

	{% block contents %}
	<div class="amk-shell">
	  <header class="amk-header">
	    <div class="amk-brand">
	      <span class="amk-wordmark">Auto<span>MeKin</span>-X</span>
	      <span class="amk-product">RXNet Visualizer</span>
	    </div>
	    <div class="amk-header-right">
	      <div class="amk-context">{{ title }}</div>
	      <a class="amk-link" href="__AMKX_URL__" target="_blank" rel="noopener" title="Official AutoMeKin-X repository">
	        <img class="amk-logo" src="data:image/png;base64,__AMK_LOGO__" alt="AutoMeKin logo">
	        <span>on GitHub &#8599;</span>
	      </a>
	    </div>
	  </header>
	  """ + "{{ super() }}" + """
	</div>
	{% endblock %}
	"""
	style_template = style_template.replace("__AMKX_URL__",amk_assets.AMKX_URL).replace("__AMK_LOGO__",amk_assets.LOGO_PNG_B64)
	posx = layout_function(G)
	# Add model field to all nodes and edges & also vibrations
	add_models(G)
	if (Nvibrations != 0):
		arx.vibr_displ_parser(finaldir,G,Nvibrations,geo_molden_update)
		add_vibr_models(G)

	# Handle the resources
	if (local_resources):
		bokeh_mode = "inline"
	else:
		bokeh_mode = "cdn"
	alt_jsmol = (len(jsmol_resources.keys()) == 3)

	# Bokeh-powered visualization via RXVisualizer
	bk_fig,bk_graph = bokeh_network_view(G,positions=posx,graph_title=title,width=w1,height=h)
	if (with_profiles):
		# Call full_view_layout() passing the graph so it loads profiles
		lay = full_view_layout(bk_fig,bk_graph,G,sizing_dict=sizing_dict,alt_jsmol=alt_jsmol,jsmol_resources=jsmol_resources)
	else:
		lay = full_view_layout(bk_fig,bk_graph,sizing_dict=sizing_dict,alt_jsmol=alt_jsmol,jsmol_resources=jsmol_resources)

	if (generate_file):
		bokeh.plotting.output_file(outfile,title=title,mode=bokeh_mode)
		bokeh.plotting.save(lay,template=style_template)
	
	return lay

def pass_args_cmd(pass_args=[]):
	'''Use argparse to pass command-line arguments to generate a visualization
	Input:
	- Args from STDIN
	- pass_args. LIst of strings allowing to run the function from the comandline
	Output:
	- args. argparse.ArgumentParser() object.
	'''
	argparser = argparse.ArgumentParser()
	argparser.add_argument("finaldir",help="Directory with AutoMeKin FINAL calculations",type=str)
	argparser.add_argument("rxnfile",help="Name of the RXNet file to use. Options: RXNet, RXNet.cg, RXNet.rel",type=str)
	g1 = argparser.add_argument_group("RXN parsing")
	g1.add_argument("--barrierless",'-b',help="Include barrierless routes from RXNet.barrless",action='store_true')
	g1.add_argument("--vibrations",'-v',help="Number of normal modes to add to visualization: use -1 for all",type=int,default=-1,metavar="NVIBR")
	g1.add_argument("--ref_state",'-rs',help="Reference state for energies",type=str,default=None)
	g2 = argparser.add_argument_group("Path handling")
	g2.add_argument("--paths",'-p',help="Generate paths from SOURCE to TARGET. If no additional args are provided, find all paths in the network",type=str,nargs="*",metavar=("SOURCE","TARGET"))
	g2.add_argument("--cutoff_path",'-c',help="Set cutoff for the path search: default 4",type=int,default=4,metavar="CUTOFF")
	g2.add_argument("--efilter","-e",help="Set energy threshold for path selection, in kcal/mol: by default no filtering is done",type=float,default=None)
	g2.add_argument("--unreduced",'-u',help="Generate full graph, without excluding nodes not in the paths",action='store_true')
	g2.add_argument("--geomolden",'-ng',help="Update geometries from MOLDEN files",action='store_true')
	g3 = argparser.add_argument_group("File handling")
	g3.add_argument("--outfile",'-o',help="Name for the HTML output file",type=str,default="network.html")
	g3.add_argument("--title",'-t',help="Title for the HTML visualization",type=str,default="Reaction network visualization")
	g4 = argparser.add_argument_group("Aspect handling")
	g4.add_argument("--resolution","-r",help="Size for the HTML visualization, of the form WIDTH,HEIGHT in pixels",type=str,default="1400,800")
	g4.add_argument("--fasterlayout","-f",help="Use the faster nx.spring_layout as default",action='store_true')
	try:
		if (pass_args):
			args = argparser.parse_args(pass_args)
		else:
			args = argparser.parse_args()
	except:
		print("finaldir and rxnfile must be passed")
		argparser.print_help()
		sys.exit()
	return args

def gen_view_cmd(args):
	'''Generate a visualization via generate_visualization() through the commandline arguments handled by pass_args_cmd()
	Input:
	- args. Filled argparse.ArgumentParser() object, from pass_args_cmd().
	Output:
	- Gwork. NetworkX.Graph object generated by RX_builder(), possibly including paths in pathList property.
	- view. Bokeh visualization from full_view_layout().
	'''
	# Read the graph
	data = arx.RX_parser(finaldir=args.finaldir,rxnfile=args.rxnfile,check_connection=True)
	if (args.barrierless):
		data_barrless = arx.RX_parser(finaldir=args.finaldir,rxnfile="RXNet.barrless")
		joined_data = [data[ii]+data_barrless[ii] for ii in range(len(data))]
		data = joined_data
	G = arx.RX_builder(finaldir=args.finaldir,data=data)

	# Manage reference state changes
	if (args.ref_state):
		arx.switch_ref_state(G,args.ref_state)
	
	# Path handling: several situations are possible: i) SOURCE and TARGET, ii) only SOURCE, iii) not SOURCE nor TARGET, iv) --paths not passed
	# For i), ii) and iii), paths shall be added, and args.paths will be a LIST
	# Also, several sources or targets can be passed, comma-separated
	paths_passed = isinstance(args.paths,list)
	if (paths_passed):
		if (len(args.paths) == 2):
			source,target = [item.split(",") for item in args.paths]
			limits = arx.node_synonym_search(G,[source,target])
		elif (len(args.paths) == 1):
			source = args.paths[0].split(",")
			target = None
			limits = arx.node_synonym_search(G,[source])
			limits.append([])
		else:
			source = None
			target = None
			limits = [[],[]]
		#args.title = " to ".join([source,target])
		paths = arx.add_paths(G,limits[0],limits[1],cutoff=args.cutoff_path)
		# Additional filters and modifications

		if (args.efilter):
			paths[:] = arx.path_filter(G,paths,args.efilter)
		
		if (not args.unreduced):
			Gwork = arx.graph_path_selector(G,paths)
		else:
			Gwork = G
	else:
		Gwork = G

	# add neighbor lists to nodes
	for nd in Gwork.nodes(data=True):
		nd[1]["neighbors"] = list(G.neighbors(nd[0]))
	# Generate the visualization, parsing the size
	width_value,height_value = [int(item) for item in args.resolution.split(",")]
	if (args.fasterlayout):
		lay_function = nx.spring_layout
	else:
		lay_function = nx.kamada_kawai_layout
	view = generate_visualization(Gwork,finaldir=args.finaldir,title=args.title,outfile=args.outfile,
								  Nvibrations=args.vibrations,with_profiles=paths_passed,size=(width_value,height_value),
								  layout_function=lay_function,geo_molden_update=args.geomolden)

	return Gwork,view

    
