from typing import List

from torch import Use

# Adapted from code by Zach Peats

# ======================================================================================================================
# Do not touch the client message class!
# ======================================================================================================================


class ClientMessage:
	"""
	This class will be filled out and passed to student_entrypoint for your algorithm.
	"""
	total_seconds_elapsed: float	  # The number of simulated seconds elapsed in this test
	previous_throughput: float		  # The measured throughput for the previous chunk in kB/s

	buffer_current_fill: float		    # The number of kB currently in the client buffer
	buffer_seconds_per_chunk: float     # Number of seconds that it takes the client to watch a chunk. Every
										# buffer_seconds_per_chunk, a chunk is consumed from the client buffer.
	buffer_seconds_until_empty: float   # The number of seconds of video left in the client buffer. A chunk must
										# be finished downloading before this time to avoid a rebuffer event.
	buffer_max_size: float              # The maximum size of the client buffer. If the client buffer is filled beyond
										# maximum, then download will be throttled until the buffer is no longer full

	# The quality bitrates are formatted as follows:
	#
	#   quality_levels is an integer reflecting the # of quality levels you may choose from.
	#
	#   quality_bitrates is a list of floats specifying the number of kilobytes the upcoming chunk is at each quality
	#   level. Quality level 2 always costs twice as much as quality level 1, quality level 3 is twice as big as 2, and
	#   so on.
	#       quality_bitrates[0] = kB cost for quality level 1
	#       quality_bitrates[1] = kB cost for quality level 2
	#       ...
	#
	#   upcoming_quality_bitrates is a list of quality_bitrates for future chunks. Each entry is a list of
	#   quality_bitrates that will be used for an upcoming chunk. Use this for algorithms that look forward multiple
	#   chunks in the future. Will shrink and eventually become empty as streaming approaches the end of the video.
	#       upcoming_quality_bitrates[0]: Will be used for quality_bitrates in the next student_entrypoint call
	#       upcoming_quality_bitrates[1]: Will be used for quality_bitrates in the student_entrypoint call after that
	#       ...
	#
	quality_levels: int
	quality_bitrates: List[float]
	upcoming_quality_bitrates: List[List[float]]

	# You may use these to tune your algorithm to each user case! Remember, you can and should change these in the
	# config files to simulate different clients!
	#
	#   User Quality of Experience =    (Average chunk quality) * (Quality Coefficient) +
	#                                   -(Number of changes in chunk quality) * (Variation Coefficient)
	#                                   -(Amount of time spent rebuffering) * (Rebuffering Coefficient)
	#
	#   *QoE is then divided by total number of chunks
	#
	quality_coefficient: float
	variation_coefficient: float
	rebuffering_coefficient: float
# ======================================================================================================================


# Your helper functions, variables, classes here. You may also write initialization routines to be called
# when this script is first imported and anything else you wish.
thoroughput_hist = []

# Harmonic mean predictor
# 5 last thoroughput values stored in a list, updated every chunk
def predicted_thoroughput(current_throughput):
	global thoroughput_hist

	if current_throughput > 0:
		thoroughput_hist.append(current_throughput)
	
	if len(thoroughput_hist) > 5:
		thoroughput_hist.pop(0) # remove elements

	if len(thoroughput_hist) == 0:
		return 0
	
	# harmonic mean formula = n / (sum of reciprocals)
	n = len(thoroughput_hist)
	sum_of_reciprocals = sum(1.0 / t for t in thoroughput_hist)

	harmonic_mean = n / sum_of_reciprocals
	return harmonic_mean

last_quality = 0
def student_entrypoint(client_message: ClientMessage):
	"""
	Your mission, if you choose to accept it, is to build an algorithm for chunk bitrate selection that provides
	the best possible experience for users streaming from your service.

	Construct an algorithm below that selects a quality for a new chunk given the parameters in ClientMessage. Feel
	free to create any helper function, variables, or classes as you wish.

	Simulation does ~NOT~ run in real time. The code you write can be as slow and complicated as you wish without
	penalizing your results. Focus on picking good qualities!

	Also remember the config files are built for one particular client. You can (and should!) adjust the QoE metrics to
	see how it impacts the final user score. How do algorithms work with a client that really hates rebuffering? What
	about when the client doesn't care about variation? For what QoE coefficients does your algorithm work best, and
	for what coefficients does it fail?

	Args:
		client_message : ClientMessage holding the parameters for this chunk and current client state.

	:return: float Your quality choice. Must be one in the range [0 ... quality_levels - 1] inclusive.
	"""

	# MPC algo 
	# look ahead into the future to decide 
	# harmonic mean of the past 5 thoroughput to predict fut
	# 1. enumerate possible quality sequences
	# 2. evalue each QoE for each sequence
	# 3. Select the first quality of the best sequence

	# Predictions are recomputed every chunk
	# brute force is accepatable in this proejct

	# Start with MPC
	# Enumerate all possible sequences
	# Use harmonic mean of previous throughputs to predict future throughput
	# Calculate QoE for each sequence using predicted throughput
	# Implement RobustMPC
	# Change predictor to return a lower bound value
	global last_quality
	predicted_bw = predicted_thoroughput(client_message.previous_throughput)
	best_qoe = float('-inf')
	best_sequence = None

	if predicted_bw <= 0:
		return 0  #no data bitrate is 0
	
	look_ahead = min(5, len(client_message.upcoming_quality_bitrates))  # look ahead up to 5 chunks

	possible_sequences = [[]]

	for i in range(look_ahead):
		new_seq = []
		for seq in possible_sequences:
			for j in range(client_message.quality_levels):
				new_seq.append(seq + [j])
		possible_sequences = new_seq

	for seq in possible_sequences:
		curr_buffer = client_message.buffer_seconds_until_empty
		total_qoe = 0
		temp_quality = last_quality

		for i, quality in enumerate(seq):

			if i == 0:
				chunk_size = client_message.quality_bitrates[quality]
			else:
				chunk_size = client_message.upcoming_quality_bitrates[i-1][quality]

			download_time = chunk_size / predicted_bw
			rebuffer_time = (download_time - curr_buffer) if download_time > curr_buffer else 0

			curr_buffer = max(0, curr_buffer - download_time) + client_message.buffer_seconds_per_chunk # buffer left + new hcunk 
			curr_buffer = min(curr_buffer, client_message.buffer_max_size)  # cap buffer at max size

			formula = (quality * client_message.quality_coefficient) - (abs(quality - temp_quality) * client_message.variation_coefficient) - (rebuffer_time * client_message.rebuffering_coefficient)

			total_qoe += formula
			temp_quality = quality

		if total_qoe > best_qoe: # save as best and keep for fut	
			best_qoe = total_qoe
			best_sequence = seq

	if best_sequence is None or len(best_sequence) == 0: # fix stuff
		return 0  

	last_quality = best_sequence[0]
	return best_sequence[0] # onlty do first stpe 


	