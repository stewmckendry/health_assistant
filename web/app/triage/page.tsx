'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ThemeToggle } from '@/components/theme-toggle';
import { Loader2, AlertCircle, Activity, Clock, FileText, ChevronRight, Home, CheckCircle } from 'lucide-react';
import Link from 'next/link';
import { FeedbackButtons } from '@/components/chat/FeedbackButtons';

interface VitalSigns {
  blood_pressure?: string;
  heart_rate?: number;
  respiratory_rate?: number;
  temperature?: number;
  oxygen_saturation?: number;
  pain_scale?: number;
}

interface TriageRequest {
  age: number;
  sex?: string;
  chief_complaint: string;
  history?: string;
  symptoms?: string[];
  vitals?: VitalSigns;
  medical_history?: string[];
  medications?: string[];
  allergies?: string[];
  session_id?: string;
}

interface TriageResponse {
  ctas_level: number;
  urgency: string;
  estimated_wait_time: string;
  disposition: string;
  red_flags: string[];
  initial_actions: string[];
  recommended_tests: string[];
  clinical_summary: string;
  confidence: number;
  assessment_id: string;
  timestamp: string;
  warnings: string[];
  session_id?: string;
}

interface StreamingUpdate {
  type: string;
  agent?: string;
  tool?: string;
  message?: string;
  progress?: number;
  result?: TriageResponse;
  data?: {
    summary?: string;
    [key: string]: any;
  };
  timestamp?: string;
}

export default function TriagePage() {
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<TriageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<StreamingUpdate[]>([]);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [useStreaming, setUseStreaming] = useState(true);
  const [traceId, setTraceId] = useState<string | null>(null);
  
  // Form state
  const [age, setAge] = useState('');
  const [sex, setSex] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [history, setHistory] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [bloodPressure, setBloodPressure] = useState('');
  const [heartRate, setHeartRate] = useState('');
  const [respiratoryRate, setRespiratoryRate] = useState('');
  const [temperature, setTemperature] = useState('');
  const [oxygenSaturation, setOxygenSaturation] = useState('');
  const [painScale, setPainScale] = useState('');
  const [medicalHistory, setMedicalHistory] = useState('');
  const [medications, setMedications] = useState('');
  const [allergies, setAllergies] = useState('');

  const handleSubmitWithStreaming = async () => {
    setIsLoading(true);
    setError(null);
    setResponse(null);
    setProgress([]);
    setCurrentProgress(0);
    setTraceId(null);

    const request: TriageRequest = {
      age: parseInt(age),
      sex: sex || undefined,
      chief_complaint: chiefComplaint,
      history: history || undefined,
      symptoms: symptoms ? symptoms.split(',').map(s => s.trim()).filter(s => s) : undefined,
      vitals: {
        blood_pressure: bloodPressure || undefined,
        heart_rate: heartRate ? parseInt(heartRate) : undefined,
        respiratory_rate: respiratoryRate ? parseInt(respiratoryRate) : undefined,
        temperature: temperature ? parseFloat(temperature) : undefined,
        oxygen_saturation: oxygenSaturation ? parseInt(oxygenSaturation) : undefined,
        pain_scale: painScale ? parseInt(painScale) : undefined,
      },
      medical_history: medicalHistory ? medicalHistory.split(',').map(s => s.trim()).filter(s => s) : undefined,
      medications: medications ? medications.split(',').map(s => s.trim()).filter(s => s) : undefined,
      allergies: allergies ? allergies.split(',').map(s => s.trim()).filter(s => s) : undefined,
      session_id: `triage_${Date.now()}`
    };

    // Remove empty vitals object if no vitals provided
    if (request.vitals && !Object.values(request.vitals).some(v => v !== undefined)) {
      delete request.vitals;
    }

    try {
      if (useStreaming) {
        // Use streaming endpoint - using relative URL like main page
        const res = await fetch('/api/agents/triage/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        });

        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  console.log('Streaming data received:', data); // Debug logging
                  
                  // Capture trace_id from any update that has it
                  if (data.trace_id && !traceId) {
                    setTraceId(data.trace_id);
                  }
                  
                  if (data.type === 'final' && data.result) {
                    // Final result
                    setResponse(data.result);
                    setCurrentProgress(100);
                  } else if (data.type === 'error') {
                    throw new Error(data.message || 'Assessment failed');
                  } else if (data.type === 'complete') {
                    // Stream complete
                    break;
                  } else {
                    // Progress update - ensure data is included
                    const update = {
                      ...data,
                      // Use timestamp + random number to ensure uniqueness
                      timestamp: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
                    };
                    setProgress(prev => [...prev, update]);
                    if (data.progress !== undefined) {
                      setCurrentProgress(data.progress);
                    }
                  }
                } catch (e) {
                  console.error('Failed to parse SSE data:', e);
                }
              }
            }
          }
        }
      } else {
        // Use regular endpoint - using relative URL like main page
        const res = await fetch('/api/agents/triage', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        });

        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }

        const data = await res.json();
        setResponse(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const loadTestCase = (caseType: string) => {
    switch(caseType) {
      case 'chest-pain':
        setAge('65');
        setSex('Male');
        setChiefComplaint('Crushing chest pain');
        setHistory('Sudden onset crushing chest pain radiating to left arm, started 30 minutes ago while at rest.');
        setSymptoms('Chest pain, Shortness of breath, Sweating, Nausea');
        setBloodPressure('150/95');
        setHeartRate('110');
        setRespiratoryRate('24');
        setTemperature('36.8');
        setOxygenSaturation('94');
        setPainScale('9');
        setMedicalHistory('Hypertension, Type 2 Diabetes, Former smoker');
        setMedications('Metoprolol, Metformin');
        break;
      case 'anaphylaxis':
        setAge('30');
        setSex('Female');
        setChiefComplaint('Difficulty breathing after bee sting');
        setHistory('Stung by bee 10 minutes ago, rapidly developing facial swelling and difficulty breathing');
        setSymptoms('Stridor, Facial swelling, Hives, Difficulty breathing');
        setBloodPressure('85/60');
        setHeartRate('130');
        setRespiratoryRate('28');
        setTemperature('36.7');
        setOxygenSaturation('91');
        setMedicalHistory('Known bee sting allergy');
        setMedications('EpiPen (not yet administered)');
        setAllergies('Bee stings');
        break;
      case 'uti':
        setAge('35');
        setSex('Female');
        setChiefComplaint('Burning with urination');
        setHistory('3 days of burning with urination and urinary frequency. No fever or back pain.');
        setSymptoms('Dysuria, Urinary frequency, Mild lower abdominal discomfort');
        setBloodPressure('118/76');
        setHeartRate('78');
        setRespiratoryRate('16');
        setTemperature('37.2');
        setOxygenSaturation('98');
        setPainScale('4');
        setMedicalHistory('Previous UTIs');
        setMedications('Oral contraceptive');
        setAllergies('Sulfa drugs');
        break;
    }
  };

  const getCTASColor = (level: number) => {
    switch(level) {
      case 1: return 'bg-red-500';
      case 2: return 'bg-orange-500';
      case 3: return 'bg-yellow-500';
      case 4: return 'bg-green-500';
      case 5: return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const handleFeedback = async (feedback: any) => {
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          traceId: feedback.traceId,
          sessionId: feedback.sessionId,
          rating: feedback.rating,
          comment: feedback.comment,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      console.log('Feedback submitted successfully');
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="sticky top-0 z-50 bg-background border-b flex-shrink-0">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="sm" className="gap-2">
                  <Home className="h-4 w-4" />
                  Back to Chat
                </Button>
              </Link>
              <div>
                <h1 className="text-2xl font-bold">Emergency Triage Assistant</h1>
                <p className="text-sm text-muted-foreground">
                  CTAS-based clinical decision support
                </p>
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 flex-1">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input Form */}
          <Card>
            <CardHeader>
              <CardTitle>Patient Information</CardTitle>
              <CardDescription>
                Enter patient details for triage assessment
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Test Cases */}
              <div className="flex gap-2 flex-wrap">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadTestCase('chest-pain')}
                >
                  Load Chest Pain Case
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadTestCase('anaphylaxis')}
                >
                  Load Anaphylaxis Case
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadTestCase('uti')}
                >
                  Load UTI Case
                </Button>
              </div>

              <Tabs defaultValue="demographics" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="demographics">Demographics</TabsTrigger>
                  <TabsTrigger value="clinical">Clinical</TabsTrigger>
                  <TabsTrigger value="vitals">Vitals</TabsTrigger>
                </TabsList>
                
                <TabsContent value="demographics" className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="age">Age *</Label>
                      <Input
                        id="age"
                        type="number"
                        value={age}
                        onChange={(e) => setAge(e.target.value)}
                        placeholder="65"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="sex">Sex</Label>
                      <Select value={sex} onValueChange={setSex}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Male">Male</SelectItem>
                          <SelectItem value="Female">Female</SelectItem>
                          <SelectItem value="Other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="clinical" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="chief-complaint">Chief Complaint *</Label>
                    <Input
                      id="chief-complaint"
                      value={chiefComplaint}
                      onChange={(e) => setChiefComplaint(e.target.value)}
                      placeholder="e.g., Chest pain"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="history">History of Present Illness</Label>
                    <Textarea
                      id="history"
                      value={history}
                      onChange={(e) => setHistory(e.target.value)}
                      placeholder="Describe onset, duration, and characteristics..."
                      rows={3}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="symptoms">Symptoms (comma-separated)</Label>
                    <Input
                      id="symptoms"
                      value={symptoms}
                      onChange={(e) => setSymptoms(e.target.value)}
                      placeholder="e.g., Chest pain, Shortness of breath, Nausea"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="medical-history">Medical History (comma-separated)</Label>
                    <Input
                      id="medical-history"
                      value={medicalHistory}
                      onChange={(e) => setMedicalHistory(e.target.value)}
                      placeholder="e.g., Hypertension, Diabetes"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="medications">Current Medications (comma-separated)</Label>
                    <Input
                      id="medications"
                      value={medications}
                      onChange={(e) => setMedications(e.target.value)}
                      placeholder="e.g., Metoprolol, Metformin"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="allergies">Allergies (comma-separated)</Label>
                    <Input
                      id="allergies"
                      value={allergies}
                      onChange={(e) => setAllergies(e.target.value)}
                      placeholder="e.g., Penicillin, Sulfa drugs"
                    />
                  </div>
                </TabsContent>

                <TabsContent value="vitals" className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="bp">Blood Pressure</Label>
                      <Input
                        id="bp"
                        value={bloodPressure}
                        onChange={(e) => setBloodPressure(e.target.value)}
                        placeholder="e.g., 120/80"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="hr">Heart Rate (bpm)</Label>
                      <Input
                        id="hr"
                        type="number"
                        value={heartRate}
                        onChange={(e) => setHeartRate(e.target.value)}
                        placeholder="e.g., 75"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="rr">Respiratory Rate</Label>
                      <Input
                        id="rr"
                        type="number"
                        value={respiratoryRate}
                        onChange={(e) => setRespiratoryRate(e.target.value)}
                        placeholder="e.g., 16"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="temp">Temperature (°C)</Label>
                      <Input
                        id="temp"
                        type="number"
                        step="0.1"
                        value={temperature}
                        onChange={(e) => setTemperature(e.target.value)}
                        placeholder="e.g., 37.0"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="spo2">O2 Saturation (%)</Label>
                      <Input
                        id="spo2"
                        type="number"
                        value={oxygenSaturation}
                        onChange={(e) => setOxygenSaturation(e.target.value)}
                        placeholder="e.g., 98"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pain">Pain Scale (0-10)</Label>
                      <Input
                        id="pain"
                        type="number"
                        min="0"
                        max="10"
                        value={painScale}
                        onChange={(e) => setPainScale(e.target.value)}
                        placeholder="0-10"
                      />
                    </div>
                  </div>
                </TabsContent>
              </Tabs>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Use Streaming</Label>
                  <input
                    type="checkbox"
                    checked={useStreaming}
                    onChange={(e) => setUseStreaming(e.target.checked)}
                    className="rounded"
                  />
                </div>

                <Button
                  className="w-full"
                  size="lg"
                  onClick={handleSubmitWithStreaming}
                  disabled={isLoading || !age || !chiefComplaint}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Assessing... {currentProgress > 0 && `(${currentProgress}%)`}
                    </>
                  ) : (
                    <>
                      <Activity className="mr-2 h-4 w-4" />
                      Perform Triage Assessment
                    </>
                  )}
                </Button>

                {/* Progress Updates */}
                {isLoading && progress.length > 0 && (
                  <Card className="mt-4">
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Progress</span>
                          <span className="font-medium">{currentProgress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-primary h-2 rounded-full transition-all duration-300"
                            style={{ width: `${currentProgress}%` }}
                          />
                        </div>
                        <div className="mt-3 space-y-1">
                          {progress.slice(-5).map((update, i) => {
                            // Format message based on update type
                            let displayContent = null;
                            
                            if (update.type === 'tool_call') {
                              displayContent = (
                                <>
                                  <Activity className="h-3 w-3 text-blue-500" />
                                  <span className="text-blue-600 font-medium">{update.tool}</span>
                                  <span className="text-muted-foreground">analyzing...</span>
                                </>
                              );
                            } else if (update.type === 'tool_result') {
                              displayContent = (
                                <>
                                  <ChevronRight className="h-3 w-3 text-green-500" />
                                  {update.data?.summary ? (
                                    <span className="text-green-600">{update.data.summary}</span>
                                  ) : (
                                    <span className="text-muted-foreground">Analysis complete</span>
                                  )}
                                </>
                              );
                            } else if (update.type === 'agent_change') {
                              displayContent = (
                                <>
                                  <ChevronRight className="h-3 w-3" />
                                  <span className="text-purple-600 font-medium">{update.agent}</span>
                                </>
                              );
                            } else if (update.type === 'progress') {
                              displayContent = (
                                <>
                                  <ChevronRight className="h-3 w-3" />
                                  <span className="text-muted-foreground">{update.message}</span>
                                  {update.data?.preview && (
                                    <span className="text-xs italic ml-2 text-muted-foreground/60">
                                      {update.data.preview.slice(0, 50)}...
                                    </span>
                                  )}
                                </>
                              );
                            } else {
                              displayContent = (
                                <>
                                  <ChevronRight className="h-3 w-3" />
                                  <span className="text-muted-foreground">{update.message}</span>
                                </>
                              );
                            }
                            
                            return (
                              <div key={update.timestamp || `update_${i}_${Date.now()}`} className="text-sm transition-all duration-300 ease-in-out">
                                <div className="flex items-center gap-2">
                                  {displayContent}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          <div className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {response && (
              <>
                {/* CTAS Level Card */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Triage Assessment</CardTitle>
                      <Badge 
                        className={`${getCTASColor(response.ctas_level)} text-white px-3 py-1 text-lg`}
                      >
                        CTAS {response.ctas_level}
                      </Badge>
                    </div>
                    <CardDescription>{response.urgency}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Wait Time</p>
                        <p className="font-medium flex items-center">
                          <Clock className="mr-1 h-4 w-4" />
                          {response.estimated_wait_time}
                        </p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Confidence</p>
                        <p className="font-medium">{(response.confidence * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                    
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Disposition</p>
                      <p className="font-medium">{response.disposition}</p>
                    </div>

                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Clinical Summary</p>
                      <p className="text-sm">{response.clinical_summary}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Red Flags */}
                {response.red_flags && response.red_flags.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <AlertCircle className="h-5 w-5 text-red-500" />
                        Red Flags Identified
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {response.red_flags.map((flag, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <ChevronRight className="h-4 w-4 mt-0.5 text-red-500 flex-shrink-0" />
                            <span className="text-sm">{flag}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                {/* Initial Actions */}
                <Card>
                  <CardHeader>
                    <CardTitle>Initial Actions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {response.initial_actions.map((action, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <ChevronRight className="h-4 w-4 mt-0.5 text-primary flex-shrink-0" />
                          <span className="text-sm">{action}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                {/* Recommended Tests */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      Recommended Tests
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {response.recommended_tests.map((test, i) => (
                        <Badge key={i} variant="secondary">
                          {test}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Warnings */}
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Important Notice</AlertTitle>
                  <AlertDescription>
                    <ul className="mt-2 space-y-1 text-sm">
                      {response.warnings.map((warning, i) => (
                        <li key={i}>{warning}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>

                {/* Feedback Section */}
                {traceId && (
                  <Card>
                    <CardContent className="pt-4">
                      <FeedbackButtons
                        traceId={traceId}
                        sessionId={response.session_id || `triage_${Date.now()}`}
                        onFeedback={handleFeedback}
                        context="triage"
                      />
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}