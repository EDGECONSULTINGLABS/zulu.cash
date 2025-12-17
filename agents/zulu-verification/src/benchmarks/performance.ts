/**
 * Performance Benchmarks (Phase 0.5)
 * Target: <10% overhead, <32MB peak memory, ≥150MB/s throughput
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { performance } from 'perf_hooks';
import { ArtifactType, CHUNK_SIZES, CommitmentStrategy } from '../types';
import { streamFileChunks, getChunkHashes } from '../chunking/deterministic';
import { calculateRootCommitment, createRootCommitment } from '../chunking/commitment';
import { hashFile } from '../crypto/blake3';

interface BenchmarkResult {
  name: string;
  fileSize: number;
  duration: number;
  throughputMBps: number;
  peakMemoryMB: number;
  overhead: number;
  passed: boolean;
}

const TARGETS = {
  maxOverhead: 0.1, // 10%
  maxMemoryMB: 32,
  minThroughputMBps: 150,
};

/**
 * Create test file
 */
async function createTestFile(sizeMB: number): Promise<string> {
  const tempDir = './temp_benchmark';
  await fs.mkdir(tempDir, { recursive: true });
  
  const filePath = path.join(tempDir, `test_${sizeMB}mb.bin`);
  const sizeBytes = sizeMB * 1024 * 1024;
  
  // Generate deterministic data (fast)
  const chunkSize = 1024 * 1024; // 1MB chunks
  const fd = await fs.open(filePath, 'w');
  
  try {
    for (let i = 0; i < sizeMB; i++) {
      const chunk = Buffer.alloc(chunkSize);
      // Fill with pattern
      for (let j = 0; j < chunkSize; j += 4) {
        chunk.writeUInt32LE((i * chunkSize + j) & 0xffffffff, j);
      }
      await fd.write(chunk);
    }
  } finally {
    await fd.close();
  }
  
  return filePath;
}

/**
 * Measure memory usage
 */
function getMemoryUsageMB(): number {
  const usage = process.memoryUsage();
  return usage.heapUsed / (1024 * 1024);
}

/**
 * Benchmark: Simple file hash (baseline)
 */
async function benchmarkBaseline(filePath: string, fileSize: number): Promise<number> {
  const startTime = performance.now();
  await hashFile(filePath);
  const duration = performance.now() - startTime;
  return duration;
}

/**
 * Benchmark: Full verification pipeline
 */
async function benchmarkVerification(
  filePath: string,
  fileSize: number,
  artifactType: ArtifactType
): Promise<BenchmarkResult> {
  const chunkSize = CHUNK_SIZES[artifactType];
  const memoryBefore = getMemoryUsageMB();
  let peakMemory = memoryBefore;
  
  const startTime = performance.now();
  
  // Step 1: Chunk and hash
  const chunks: any[] = [];
  for await (const chunk of streamFileChunks(filePath, chunkSize)) {
    chunks.push({
      index: chunk.index,
      hash: chunk.hash,
    });
    
    // Track peak memory
    const currentMemory = getMemoryUsageMB();
    if (currentMemory > peakMemory) {
      peakMemory = currentMemory;
    }
  }
  
  // Step 2: Calculate root commitment
  const chunkHashes = chunks.map(c => c.hash);
  const root = calculateRootCommitment(
    CommitmentStrategy.SIMPLE_CONCAT_V1,
    chunkHashes
  );
  
  const duration = performance.now() - startTime;
  const throughputMBps = (fileSize / (duration / 1000));
  const memoryUsed = peakMemory - memoryBefore;
  
  // Calculate overhead vs baseline
  const baselineDuration = await benchmarkBaseline(filePath, fileSize);
  const overhead = (duration - baselineDuration) / baselineDuration;
  
  const passed = 
    overhead <= TARGETS.maxOverhead &&
    memoryUsed <= TARGETS.maxMemoryMB &&
    throughputMBps >= TARGETS.minThroughputMBps;
  
  return {
    name: `Verify ${fileSize}MB ${artifactType}`,
    fileSize,
    duration,
    throughputMBps,
    peakMemoryMB: memoryUsed,
    overhead,
    passed,
  };
}

/**
 * Run all benchmarks
 */
export async function runBenchmarks(): Promise<void> {
  console.log('🚀 Starting Zulu Verification Benchmarks');
  console.log('='.repeat(70));
  console.log(`Targets: <${TARGETS.maxOverhead * 100}% overhead, <${TARGETS.maxMemoryMB}MB memory, ≥${TARGETS.minThroughputMBps}MB/s\n`);
  
  const results: BenchmarkResult[] = [];
  
  try {
    // Benchmark 100MB file (main target)
    console.log('Creating 100MB test file...');
    const testFile100 = await createTestFile(100);
    
    console.log('\n📊 Benchmarking MODEL artifact (1MiB chunks)...');
    const result100 = await benchmarkVerification(testFile100, 100, ArtifactType.MODEL);
    results.push(result100);
    printResult(result100);
    
    // Benchmark different chunk sizes
    console.log('\n📊 Benchmarking MEMORY artifact (64KiB chunks)...');
    const result100Mem = await benchmarkVerification(testFile100, 100, ArtifactType.MEMORY);
    results.push(result100Mem);
    printResult(result100Mem);
    
    console.log('\n📊 Benchmarking PLUGIN artifact (256KiB chunks)...');
    const result100Plugin = await benchmarkVerification(testFile100, 100, ArtifactType.PLUGIN);
    results.push(result100Plugin);
    printResult(result100Plugin);
    
    console.log('\n📊 Benchmarking UI artifact (512KiB chunks)...');
    const result100UI = await benchmarkVerification(testFile100, 100, ArtifactType.UI);
    results.push(result100UI);
    printResult(result100UI);
    
    // Summary
    console.log('\n' + '='.repeat(70));
    console.log('📈 BENCHMARK SUMMARY');
    console.log('='.repeat(70));
    
    const allPassed = results.every(r => r.passed);
    const avgThroughput = results.reduce((sum, r) => sum + r.throughputMBps, 0) / results.length;
    const avgOverhead = results.reduce((sum, r) => sum + r.overhead, 0) / results.length;
    const maxMemory = Math.max(...results.map(r => r.peakMemoryMB));
    
    console.log(`Overall: ${allPassed ? '✅ PASSED' : '❌ FAILED'}`);
    console.log(`Average Throughput: ${avgThroughput.toFixed(2)} MB/s`);
    console.log(`Average Overhead: ${(avgOverhead * 100).toFixed(2)}%`);
    console.log(`Peak Memory: ${maxMemory.toFixed(2)} MB`);
    
    // Cleanup
    await fs.rm('./temp_benchmark', { recursive: true, force: true });
    
    if (!allPassed) {
      process.exit(1);
    }
    
  } catch (error) {
    console.error('❌ Benchmark failed:', error);
    await fs.rm('./temp_benchmark', { recursive: true, force: true });
    process.exit(1);
  }
}

/**
 * Print benchmark result
 */
function printResult(result: BenchmarkResult): void {
  const status = result.passed ? '✅' : '❌';
  console.log(`${status} ${result.name}`);
  console.log(`   Duration: ${result.duration.toFixed(2)}ms`);
  console.log(`   Throughput: ${result.throughputMBps.toFixed(2)} MB/s (target: ≥${TARGETS.minThroughputMBps})`);
  console.log(`   Memory: ${result.peakMemoryMB.toFixed(2)} MB (target: <${TARGETS.maxMemoryMB})`);
  console.log(`   Overhead: ${(result.overhead * 100).toFixed(2)}% (target: <${TARGETS.maxOverhead * 100}%)`);
}

// Run if called directly
if (require.main === module) {
  runBenchmarks().catch(console.error);
}
