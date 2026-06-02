// Command server starts a gRPC server exposing the Factorizer service.

// It implements all three RPC patterns from the proto so you can see how
// each one is wired on the server side.

package main

import (
	"context"
	"io"
	"log"
	"net"
	"time"

	pb "example.com/grpc_poc/gen/go/factorizepb"

	"google.golang.org/grpc"
)

const listenAddr = ":50051"

// server implements pb.FactorizerServer.
// Embedding UnimplementedFactorizerServer keeps the server compiling even if
// new RPCs are later added to the proto (forward compatibility)
type server struct {
	pb.UnimplementedFactorizerServer
}

// --- Domain logic: prime factorization ---

// factorize returns the prime factorization of n as (prime, exponent) pairs.
// Optimized trial division: test 2, then only odd divisors up to sqrt(n).
// For very large n you would swap this for Pollard's rho + Miller-Rabin;
// the gRPC plumbing around it stays identical.
func factorize(n uint64) []*pb.PrimeFactor {
	factors := make([]*pb.PrimeFactor, 0, 8)

	addFactor := func(prime uint64, exp uint32) {
		factors = append(factors, &pb.PrimeFactor{Prime: prime, Exponent: exp})
	}

	// Strip factors of 2 first so we can step by afterwards.
	if n%2 == 0 {
		var exp uint32
		for n%2 == 0 {
			n /= 2
			exp++
		}
		addFactor(2, exp)
	}

	// Test odd divisors d while d*d <= n.
	for d := uint64(3); d*d <= n; d += 2 {
		if n%d == 0 {
			var exp uint32
			for n%d == 0 {
				n /= d
				exp++
			}
			addFactor(d, exp)
		}
	}

	if n > 1 {
		addFactor(n, 1)
	}
	return factors
}


// compute wraps factorize and measures server-side compute time.
func compute(value uint64) *pb.FactorizeResponse {
	start := time.Now()
	factors := factorize(value)
	return &pb.FactorizeResponse{
		Value:         value,
		Factors:       factors,
		ElapsedMicros: uint64(time.Since(start).Microseconds()),
	}
}

// --- RPC handlers ----------------------------------------------------------

// Factorize is the unary handler: receive one request, return one response.
func (s *server) Factorize(ctx context.Context, req *pb.FactorizeRequest) (*pb.FactorizeResponse, error) {
	return compute(req.GetValue()), nil
}

// FactorizeBatch is the server-streaming handler: one request in, many
// responses pushed back. stream.Send() flushes each result immediately,
// so the client starts receiving before the whole batch is done.
func (s *server) FactorizeBatch(req *pb.FactorizeBatchRequest, stream pb.Factorizer_FactorizeBatchServer) error {
	for _, v := range req.GetValues() {
		if err := stream.Send(compute(v)); err != nil {
			return err // client went away / transport error
		}
	}
	return nil // returning nil cleanly closes the server stream
}

// FactorizeStream is the bidirectional handler: read requests and write
// responses on the same connection until the client closes its send side
// (signalled by io.EOF on Recv).
func (s *server) FactorizeStream(stream pb.Factorizer_FactorizeStreamServer) error {
	for {
		req, err := stream.Recv()
		if err == io.EOF {
			return nil // client closed its half -> we close ours by returning
		}
		if err != nil {
			return err
		}
		if err := stream.Send(compute(req.GetValue())); err != nil {
			return err
		}
	}
}

func main() {
	lis, err := net.Listen("tcp", listenAddr)
	if err != nil {
		log.Fatalf("listen: %v", err)
	}

	s := grpc.NewServer()
	pb.RegisterFactorizerServer(s, &server{})

	log.Printf("Factorizer gRPC server listening on %s", listenAddr)
	if err := s.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

