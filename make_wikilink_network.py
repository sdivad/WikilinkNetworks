import codecs
import sys
import re
from wikitools import wiki
from wikitools import api


name = sys.argv[1]
data_folder = 'data/'
if len(sys.argv)>2:
	data_folder = sys.argv[2].strip('/') +'/'


verbose = True
very_verbose = False

linkSimpleP = re.compile(r'\[\[(.+?)[][|{}/#]') 
linkGreedyP = re.compile(r'\[\[([^]^[^}^{^#^/^|]+)')
linkP = re.compile(r'\[\[([^]^[^}^{^#^/^]+?)\s*(?:/[^]^[]*?)?\s*(?:\|[^]^[]*?)?(?:\}\})?\s*\]\]')


# create a Wiki object
site = wiki.Wiki("http://en.wikipedia.org/w/api.php") 


p_id = 0

outlinks_file = codecs.open(data_folder + name + '_network.csv', 'w', 'UTF-8')
outlinks_all_file = codecs.open(data_folder + name + '_outlinks_all.csv', 'w', 'UTF-8')

outdegree_file = codecs.open(data_folder + name + '_tot_outdegree.csv', 'w', 'UTF-8')
outdegree_file.write('title' + '\t' + 'id' + '\t' + 'outdegree' + '\t' + 'outdegree_wikipedia' + '\n')	

log = codecs.open(data_folder + 'extract_network_' + name + '.log', 'a', 'UTF-8')


def main():
	page_list = load_dic(data_folder + name)
	
	tot_local_links = 0
	
	#~ if single_query:
		#~ page_list_string = ''
		#~ for page in page_list[]
			#~ page_list_string += page + '|'
		#~ page_list_string.strip('|')	
#~ 
	#~ if single_query:
		#~ pl_params = {'action':'query', 'prop':'links', 'titles':page_list_string, 'plnamespace':0, 'pllimit': 500, 'redirects':1}


	for title in page_list:
		(p, outlinks) = extract_outlinks(title)
		#~ if p > 0:
			#~ nodes[title] = p_id
		
		(redirects, outlinks_checked) = check_redirects(outlinks)
		if verbose: print '%d links (%d total) from: %s' %(len(outlinks_checked), len(outlinks), title)	
					
		tot_outdegree = len(outlinks_checked)
		local_outdegree = 0		
		for target in outlinks_checked:
			outlinks_all_file.write( title + '\t' + target + '\n')
			if target in page_list:
				local_outdegree += 1
				outlinks_file.write( title + '\t' + target  + '\n')  #'\t'.join(map(str, (p, title, pl['title']))) + '\n')				
					
		outdegree_file.write(title + '\t' + str(p) + '\t' + str(local_outdegree) + '\t' + str(tot_outdegree) + '\n')	
		if verbose: print '   ' +  str(local_outdegree) + ' internal links, ' + str(tot_outdegree) + ' total links'
		tot_local_links += local_outdegree

	if verbose: print str(tot_local_links) + ' links written'

	outlinks_file.close()
	outlinks_all_file.close()
	outdegree_file.close()


def load_dic(file_name):
	dic = {}
	f = codecs.open(file_name, 'r', 'UTF-8')
	for line in f:
		el = line.strip('\n')
		if el != '' and el != ' ' and el[0] != '#':
			dic[el] = 1
	return dic


def extract_outlinks(title):
	p_id = -1
	outlinks = []
	if title == '' or title == ' ': return p_id, outlinks
	#~ if verbose: print title + ': retrieving outgoing links from text'

	params = {'action':'query', 'prop':'revisions', 'titles':title, 'rvprop':'content', 'redirects':1} #, 'pllimit': 500, 'redirects':1}
	request = api.APIRequest(site, params)

	if very_verbose: print ('   ' + 'query: ' + str(params))
	result = request.query()
	if int(result['query']['pages'].keys()[0]) < 1:
		print 'ARTICLE NOT FOUND: ' + title
		log.write(title + '\n')
		return p_id, outlinks
		#~ p_id = result['query']['pages'][0]
			
	else:	
		outlinks = []
		#~ if verbose: print ('   ' + str(len(pl_result['query']['pages'].values()[0]['revisions'])) + ' links')
		for p in result['query']['pages']:
			p_id = p
			for rev in result['query']['pages'][p]['revisions']:
				content = rev['*']	
				links = parse_text(content)
				for l in links:
					target = l.replace(' ', '_')
					outlinks.append(target) 
				
				#it should not iterate more than once (maybe it should not be a for loop...)
				return p_id, outlinks
		return p_id, outlinks		


def parse_text(content):
	links = {}
	rough_links = re.findall(linkP, content)
	
	#~ if len(links) > 50:
		
	title_lists = list2params(rough_links)	
	for title_list in title_lists:
	
		params = {'action':'query', 'titles':title_list, 'redirects':1} #, 'pllimit': 500, 'redirects':1}
		request = api.APIRequest(site, params)
		if very_verbose: print ('   ' + 'query: ' + str(params))
		result = request.query()

		for page in result['query']['pages']:
			if page != '-1' and 'ns' in result['query']['pages'][page]:
				if result['query']['pages'][page]['ns'] == 0: 
					link = result['query']['pages'][page]['title'] #.replace(' ', '_')
					links[link] = 1
	
	return links
	

def check_redirects(titles):
	
	redirects = {}
	links = {}
	duplicates = 0
	
	title_lists = list2params(titles)	
	for title_list in title_lists:
	
		params = {'action':'query', 'titles':title_list, 'redirects':1} #, 'pllimit': 500, 'redirects':1}
		request = api.APIRequest(site, params)
		if very_verbose: print ('   ' + 'query: ' + str(params))
		result = request.query()
		
		if very_verbose: print result

		if 'redirects' in result['query']:
			for redir in result['query']['redirects']:
				redirects[redir['from']] = redir['to']

		for page in result['query']['pages']:
			if page != '-1' and 'ns' in result['query']['pages'][page]:
				if result['query']['pages'][page]['ns'] == 0: 
					link = result['query']['pages'][page]['title'].replace(' ', '_')
					if link in links:
						duplicates += 1
					links[link] = page
	
	missing = len(titles) - (len(links) + duplicates)				
	if very_verbose and missing != 0: 
		print '%d missing redirects (%d titles,  %d found, %d duplicates)' %(missing, len(titles), len(links), duplicates)
	return redirects,links


def list2param_only50(list):
	if len(list) < 1: return ''
	s = ''
	for el in list:
		s += el + '|'
	return (s.strip('|'))
		
	
def list2params(list):
	if len(list) < 1: return ''
	s = ['']
	l = 0
	i = 0
		
	for el in list:
		i += 1
		if i%50 == 0:
			s[l].strip('|')
			l += 1
			s.append('')	
		s[l] += el + '|'
	return s
	

if __name__ == '__main__':	
	main()
