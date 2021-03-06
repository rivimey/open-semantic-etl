import os.path
import sys
import subprocess
import tempfile
import enhance_ocr
import enhance_ocr_descew

# Extract text from all extracted images from pdf
# if splitpages is off, return one txt instead of page based list of texts
def pdfimages2text(filename, lang='eng', verbose=False, pdf_ocr=True, pdf_ocr_descew=False):

	ocr_txt = {}
	ocr_descew_txt = {}

	ocr_temp_dirname = tempfile.mkdtemp(prefix="opensemanticetl_pdf_ocr_")
	
	# Extract all images of the pdf to tempdir with commandline tool "pdfimages" from poppler pdf toolbox
	# -j = export as JPEG
	# -p = write page name in image filename
	result = subprocess.call(['pdfimages', '-p' ,'-j', filename, ocr_temp_dirname + os.path.sep + 'image'])

	if result == 0:

		images = os.listdir(ocr_temp_dirname)
		images.sort()

		for image in images:

			imagefilename = ocr_temp_dirname + os.path.sep + image


			if pdf_ocr:

				try:
					# extract page number from extracted image filename (image-pagenumber-imagenumber.jpg)
					pagenumber = int( image.split('-')[1] )
	
					
					result = enhance_ocr.image2text(filename=imagefilename, lang=lang, verbose=verbose)
					
					if result:
						
						if pagenumber in ocr_txt:
							ocr_txt[pagenumber] += '\n' + result
						else:
							ocr_txt[pagenumber] = result

				except KeyboardInterrupt:
					raise KeyboardInterrupt

				except BaseException as e:
					sys.stderr.write( "Exception while OCR of PDF: {} - maybe corrupt image: {} - exception: {}".format(filename, imagefilename, e) )


			if pdf_ocr_descew:

				try:
	
					# extract page number from extracted image filename (image-pagenumber-imagenumber.jpg)
					pagenumber = int( image.split('-')[1] )

					result = enhance_ocr_descew.optimized_image2text(imagefilename, lang, verbose=verbose)
					
					if result:
	
						if pagenumber in ocr_descew_txt:
							ocr_descew_txt[pagenumber] += '\n\n' + result
						else:
							ocr_descew_txt[pagenumber] = result

				except KeyboardInterrupt:
					raise KeyboardInterrupt

				except BaseException as e:

					sys.stderr.write( "Exception while optimized ocr pdf: {} - maybe corrupt image: {} - exception: {}".format(filename, imagefilename, e) )

			os.remove(imagefilename)

		os.rmdir(ocr_temp_dirname)

	else:
		sys.stderr.write( "Error: Extracting images from PDF failed for {} {}".format(filename, result) )
		
	return ocr_txt, ocr_descew_txt



def enrich_pdf ( parameters={}, data={} ):

	verbose = False
	if 'verbose' in parameters:
		if parameters['verbose']:	
			verbose = True

	filename = parameters['filename']

	if 'enhance_ocr_descew' in parameters['plugins']:
		pdf_ocr_descew = True
	else:
		pdf_ocr_descew = False

	if 'ocr_lang' in parameters:
		lang = parameters['ocr_lang']
	else:
		lang = 'eng'
		
	ocr_txt = {}
	ocr_optimized_txt = {}

	try:
		ocr_txt, ocr_optimized_txt = pdfimages2text(filename=filename, lang=lang, verbose=verbose, pdf_ocr=True, pdf_ocr_descew=pdf_ocr_descew)

	except KeyboardInterrupt:
		raise KeyboardInterrupt

	except BaseException as e:
		sys.stderr.write( "Exception while OCR the PDF {} - {}\n".format(filename, e) )

	parameters['enhance_pdf_ocr'] = ocr_txt
	parameters['enhance_pdf_ocr_descew'] = ocr_optimized_txt

	# create text field ocr_t with all OCR results of all pages
	data['ocr_t'] = ''
	for ocr_page in ocr_txt:
		
		# if yet text there, add new line before adding
		if len(data['ocr_t']) > 0:
			data['ocr_t'] += "\n"

		data['ocr_t'] += ocr_txt[ocr_page]

	if pdf_ocr_descew:
		
		data['ocr_descew_t'] = ''
		for ocr_page in ocr_optimized_txt:
			if len(data['ocr_descew_t']) > 0:
				data['ocr_descew_t'] += "\n"
			data['ocr_descew_t'] += ocr_optimized_txt[ocr_page]
			

	# Mark document to enhanced with this plugin
	data['etl_enhance_pdf_ocr_b'] = True
			
	return parameters, data
			

#
# Process plugin
#
# check if content type PDF, if so start enrich pdf process for OCR
#

class enhance_pdf_ocr(object):
	
	# how to find uris which are not enriched yet?
	# (if not enhanced on indexing but later)

	# this plugin needs to read the field id as a parameters to enrich unenriched docs
	fields = ['id', 'content_type']

	# query to find documents, that were not enriched by this plugin yet
	# (since we marked documents which were OCRd with ocr_b = true
	query = "(content_type:application\/pdf*) AND NOT (etl_enhance_pdf_ocr_b:true)"


	def process (self, parameters={}, data={} ):
	
	
		verbose = False
		if 'verbose' in parameters:
			if parameters['verbose']:	
				verbose = True

		filename = parameters['filename']

		if 'content_type' in data:
			mimetype = data['content_type']
		else:
			mimetype = parameters['content_type']

		#if connector returns a list, use only first value (which is the only entry of the list)
		if isinstance(mimetype, list):
			mimetype = mimetype[0]

	
		if "application/pdf" in mimetype.lower() or filename.lower().endswith('.pdf'):
			if verbose:
				print ( 'Mimetype is PDF ({}) or file ending is PDF, starting OCR of embedded images'.format(mimetype) )
	
			parameters, data = enrich_pdf ( parameters, data )
	
		return parameters, data
